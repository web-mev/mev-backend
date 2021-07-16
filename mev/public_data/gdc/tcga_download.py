import requests
import json
import re
import tarfile
import sys
import os
import pandas as pd
import datetime
import shutil

import gdc_data_dict

# Some constants
GDC_FILES_ENDPOINT = "https://api.gdc.cancer.gov/files"
GDC_DATA_ENDPOINT = "https://api.gdc.cancer.gov/data"

# We look for HTSeq-based counts from TCGA
HTSEQ_SUFFIX = 'htseq.counts.gz'
FILTERS = {
    "op": "and",
    "content":[
        {
        "op": "in",
        "content":{
            "field": "files.cases.project.program.name",
            "value": ["TCGA"]
            }
        },
        # Uncomment to filter on the TCGA cancer types:
        # mainly used for testing on a smaller subset of data
        #{
        #"op": "in",
        #"content":{
        #    "field": "files.cases.project.project_id",
        #    "value": ["TCGA-UVM", "TCGA-MESO"]
        #    }
        #},
        {
        "op": "in",
        "content":{
            "field": "files.analysis.workflow_type",
            "value": ["HTSeq - Counts"]
            }
        },
        {
        "op": "in",
        "content":{
            "field": "files.experimental_strategy",
            "value": ["RNA-Seq"]
            }
        },
        {
        "op": "in",
        "content":{
            "field": "files.data_type",
            "value": ["Gene Expression Quantification"]
            }
        }
    ]
}

# The count files include counts to non-genic features. We don't want those
# in our final assembled count matrix
SKIPPED_FEATURES = [
    '__no_feature', 
    '__ambiguous',
    '__too_low_aQual', 
    '__not_aligned', 
    '__alignment_not_unique'
]

# How many records to return with each query
PAGE_SIZE = 100

# This defines which fields are returned from the data query. These are the top-level
# fields. Most of the interesting clinical data is contained in the "expandable" fields
# which are given below.
FIELDS = [
    'file_id',
    'file_name',
    'cases.project.program.name',
    'cases.case_id',
    'cases.aliquot_ids',
    'cases.samples.portions.analytes.aliquots.aliquot_id'
]

# These "expandable" fields have most of the metadata we are interested in.
# By asking for these in the query, we get back info about race, gender, etc.
EXPANDABLE_FIELDS = [
    'cases.demographic',
    'cases.diagnoses',
    'cases.exposures',
    'cases.tissue_source_site',
    'cases.project'
]

# For the request, a GET is used, so the filter parameters should be passed as a JSON string.
QUERY_PARAMS = {
    "filters": json.dumps(FILTERS),
    "fields": ','.join(FIELDS),
    "format": "JSON",
    # cast this int as a string since it becomes a url param:
    "size": str(PAGE_SIZE),
    "expand": ','.join(EXPANDABLE_FIELDS)
}


def remove_column(df, columns_to_remove):
    '''
    Subsets a given dataframe given a list of columns to remove. Returns a dataframe
    WITHOUT those columns.
    '''
    keep_cols = [x for x in df.columns if not x in columns_to_remove]
    return df[keep_cols]


def merge_with_full_record(full_record, returned_data, aliquot_ids, extra_fields=None):
    '''
    The GDC "data dictionary" has keys for demographic, diagnosis, etc.
    Each of those keys addresses a list with items like:
      {
         "field": "smokeless_tobacco_quit_age",
         "description": null
      },
      {
         "field": "smoking_frequency",
         "description": "The text term used to generally decribe how often the patient smokes."
      },
      ...

    In the real data, we may not have some of these fields as the metadata is incomplete
    or not a relevant field for a particular case. This function merges the "full" description (all possible 
    fields according to the GDC data dictionary) with the actual data given.

    The `returned_data` field is a list of dicts. For instance, it could look like
    [
      {
        "synchronous_malignancy": "No",
        ...
        "tumor_stage": "stage iva"
      },
      ...
      {
        "synchronous_malignancy": "Yes",
        ...
        "tumor_stage": "stage iva"
      }
    ]

    e.g.:
        >>> mock_data_dict = [
        ...   {'field': 'a', 'description':''},
        ...   {'field': 'c', 'description':''},
        ...   {'field': 'b', 'description':''},
        ...   {'field': 'd', 'description':''},
        ...   {'field': 'e', 'description':''},
        ... ]
        >>> 
        >>> returned_data = [
        ...   {'c':13, 'a':11},
        ...   {},
        ...   {'a':31, 'b':32, 'c':33, 'd':34}
        ... ]
        >>> 
        >>> aliquot_ids = ['a1','a2','a3']
        >>> 
        >>> merge_with_full_record(mock_data_dict, returned_data, aliquot_ids)
            a     c     b     d   e
        a1  11.0  13.0   NaN   NaN NaN
        a2   NaN   NaN   NaN   NaN NaN
        a3  31.0  33.0  32.0  34.0 NaN

    Note that the `extra_fields` kwarg allows us to add more info
    that is NOT in the data dict. For instance, the data dictionary
    for the 'project' attribute (available from 
    https://api.gdc.cancer.gov/v0/submission/_dictionary/{attribute}?format=json) 
    does not define the 'project_id' field. HOWEVER, the payload returned from the file
    query API DOES have this field listed. Thus, to have the TCGA ID as part of the 
    final data, we pass "project_id" within a list via that kwarg.

    Thus,
    full_record: is a list of dicts. Each dict has (at minimum) `name` and `description` keys.
    returned_data: a list of dicts for a set of aliquots. This comes from a paginated query of actual cases
    aliquot_ids: The unique aliquot IDs, which will name the rows (the dataframe index)
    '''
    _fields = [ k['field'] for k in full_record ]

    # Note that the columns kwarg doesn't lose the association of the data and columns.
    # It's NOT like a brute-force column renaming. Instead, it just reorders the columns
    # that already exist
    df = pd.DataFrame(returned_data, index=aliquot_ids, columns=_fields)

    if extra_fields:
        other_df = pd.DataFrame(returned_data, index=aliquot_ids)[extra_fields]
        df = pd.merge(df, other_df, left_index=True, right_index=True)
    return df


finished = False
i = 0
downloaded_archives = []


'''
Below, `data_fields` is a multi-level dictionary which is a "reference" for all available
metadata fields. 
The keys at the top-level of this dict are things like demographic, diagnoses, etc.
Call those 'categories'.
Each one of those keys/categories, in turn, references a list. The list contains fields that are
defined for that category. For instance, the 'demographic' category looks (in part) like:
[
  {
    "field": "age_at_index",
    "description": "The patient's age (in years) on the reference or anchor date date used during date obfuscation."
  },
   ...
  {
    "field": "cause_of_death",
    "description": "Text term to identify the cause of death for a patient."
  }
] 
'''
data_fields = gdc_data_dict.get_data_dict()

# We have to keep a map of the fileId to the aliquot so we can properly 
# concatenate the files later
file_to_aliquot_mapping = {}
annotation_df = pd.DataFrame()
while not finished:
    print('Batch %d ...' % i)

    # the records are paginated, so we have to keep track of which page we are currently requesting
    start_index = i*PAGE_SIZE
    end_index = (i+1)*PAGE_SIZE
    QUERY_PARAMS.update(
        {
            'from': start_index
        }
    )

    response = requests.get(GDC_FILES_ENDPOINT, params = QUERY_PARAMS)
    response_json = json.loads(response.content.decode("utf-8"))

    # If the first request, we can get the total records by examining
    # the pagination data
    if i == 0:
        pagination_response = response_json['data']['pagination']
        total_records = int(pagination_response['total'])

    # now collect the file UUIDs and download
    file_uuid_list = []
    case_id_list = []
    exposures = []
    diagnoses = []
    demographics = []
    projects = []
    aliquot_ids = []

    for hit in response_json['data']['hits']:
        file_uuid_list.append(hit['file_id'])

        # hit['cases'] is a list. To date, have only seen length of 1, and unsure what a greater length would mean.
        if len(hit['cases']) > 1:
            sys.stderr.write('Encountered an unexpected issue when iterating through the returned hits.'
                ' We expect the "cases" key for a hit to be of length 1, but this was greater.'
            )
            sys.exit(1)

        case_item = hit['cases'][0]
        case_id_list.append(case_item['case_id'])

        try:
            exposures.append(case_item['exposures'][0])
        except KeyError as ex:
            exposures.append({})

        try:
            diagnoses.append(case_item['diagnoses'][0])
        except KeyError as ex:
            diagnoses.append({})

        try:
            demographics.append(case_item['demographic'])
        except KeyError as ex:
            demographics.append({})

        try:
            projects.append(case_item['project'])
        except KeyError as ex:
            projects.append({})

        try:
            aliquot_ids.append(case_item['samples'][0]['portions'][0]['analytes'][0]['aliquots'][0]['aliquot_id'])
        except KeyError as ex:
            # Need an aliquot ID to uniquely identify the column. Fail out
            raise ex

    file_to_aliquot_mapping.update(dict(zip(file_uuid_list, aliquot_ids)))

    exposure_df = merge_with_full_record(
        data_fields['exposure'], 
        exposures, 
        aliquot_ids
    )

    demographic_df = merge_with_full_record(
        data_fields['demographic'], 
        demographics, 
        aliquot_ids
    )

    diagnoses_df = merge_with_full_record(
        data_fields['diagnosis'], 
        diagnoses, 
        aliquot_ids
    )

    project_df = merge_with_full_record(
        data_fields['project'], 
        projects, 
        aliquot_ids,
        extra_fields = ['project_id']
    )

    # Remove the extra project_id column from the exposure, demo, and diagnoses dataframes. Otherwise we get duplicated
    # columns that we have to carry around:
    columns_to_remove = ['project_id',]
    exposure_df = remove_column(exposure_df, columns_to_remove)
    diagnoses_df = remove_column(diagnoses_df, columns_to_remove)
    demographic_df = remove_column(demographic_df, columns_to_remove)

    # Now merge all the dataframes (concatenate horizontally)
    # to get the full metadata/annotations
    ann_df = pd.concat([
        exposure_df,
        demographic_df,
        diagnoses_df,
        project_df
    ], axis=1)

    # Create another series which maps the aliquot IDs to the case ID.
    # That will then be added to the annotation dataframe so we know which 
    # metadata is mapped to each case
    s = pd.Series(dict(zip(aliquot_ids, case_id_list)), name='case_id')

    ann_df = pd.concat([ann_df, s], axis=1)

    # Add to the master dataframe
    annotation_df = pd.concat([annotation_df, ann_df], axis=0)

    # Download the actual expression data corresponding to the aliquot metadata
    # we've been collecting
    download_params = {"ids": file_uuid_list}
    download_response = requests.post(GDC_DATA_ENDPOINT, 
        data = json.dumps(download_params), 
        headers = {"Content-Type": "application/json"}
    )
    response_head_cd = download_response.headers["Content-Disposition"]
    file_name = re.findall("filename=(.+)", response_head_cd)[0]
    with open(file_name, "wb") as output_file:
        output_file.write(download_response.content)
    downloaded_archives.append(file_name)

    i += 1

    # are we done yet???
    if end_index >= total_records:
        finished = True

# Write all the metadata to a file
now = datetime.datetime.now()
date_str = now.strftime('%m%d%Y')
annotation_df.to_csv('annotations.{dt}.csv'.format(dt=date_str), sep=',', index_label = 'id')

# Now concatenate all the downloaded archives...
count_df = pd.DataFrame()
tmpdir = './tmparchive'
for f in downloaded_archives:
    with tarfile.open(f, 'r:gz') as tf:
        tf.extractall(path=tmpdir)
        for t in tf.getmembers():
            if t.name.endswith(HTSEQ_SUFFIX):
                file_id = t.name.split('/')[0]
                df = pd.read_table(
                    os.path.join(tmpdir, t.path), 
                    index_col=0, 
                    header=None, 
                    names=['gene', file_to_aliquot_mapping[file_id]])
                count_df = pd.concat([count_df, df], axis=1)

# remove the skipped rows which don't correspond to actual gene features
count_df = count_df.loc[~count_df.index.isin(SKIPPED_FEATURES)]
count_df.to_csv('tcga.htseq_count_matrix.{dt}.tsv'.format(dt=date_str), sep='\t')

# Clean up:
shutil.rmtree(tmpdir)
[os.remove(x) for x in downloaded_archives]
