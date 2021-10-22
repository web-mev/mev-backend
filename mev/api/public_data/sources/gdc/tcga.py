import copy
import re
import json
import logging
import requests
import datetime
import shutil
import os
import tarfile
 
import pandas as pd

from django.conf import settings
from requests.api import get

from api.utilities.basic_utils import get_with_retry, make_local_directory
from .gdc import GDCDataSource

logger = logging.getLogger(__name__)

class TCGADataSource(GDCDataSource):
    '''
    A general class for pulling data from TCGA, exposed via the GDC API
    '''

    # All the TCGA-based data will be stored in this directory
    ROOT_DIR = os.path.join(settings.PUBLIC_DATA_DIR, 'tcga')

    # This list helps to define the full filter used in the child classes.
    # Each item in this list (dicts) conforms to the GDC query syntax. We
    # don't implement checks for valid queries here, but rather rely on the GDC
    # API
    # Note that any items here will ultimately be "concatenated" using a logical
    # AND operation
    TCGA_FILTERS = [
        {
            "op": "in",
            "content":{
                "field": "files.cases.project.program.name",
                "value": ["TCGA"]
                }
        }
    ]

    def __init__(self):
        if not os.path.exists(self.ROOT_DIR):
            logger.info('When instantiating an instance of TCGADataSource, the'
                ' expected directory did not exist. Go create it...'
            )
            make_local_directory(self.ROOT_DIR)

    def _create_python_compatible_tcga_id(self, tcga_type):
        '''
        When adding datasets or groups to a HDF5 file, need to modify
        the name or it will not address properly
        '''
        return tcga_type.replace('-', '_').lower()

    def download_and_prep_dataset(self):
        pass

    def query_for_tcga_types(self):
        '''
        Gets a list of the available TCGA types from the GDC.

        Helps with organizing the data, so we can leverage HDF5 
        stored matrices
        '''
        filters = {
            'op':'in', 
            'content':{
                'field':'program.name', 
                'value':'TCGA'
            }
        }
        fields = ['program.name',]
        query_params = self.create_query_params(
            fields,
            page_size = 100, # gets all types at once
            filters = json.dumps(filters)
        )
        r = get_with_retry(GDCDataSource.GDC_PROJECTS_ENDPOINT, params=query_params)
        response_json = r.json()
        tcga_cancer_types = [x['id'] for x in response_json['data']['hits']]
        return tcga_cancer_types

    def create_cancer_specific_filter(self, tcga_cancer_id):
        '''
        Creates/returns a filter for a single TCGA type (e.g. TCGA-BRCA)

        This filter (a dict) can be directly added to a filter array
        '''
        return {
            "op": "in",
            "content":{
                "field": "files.cases.project.project_id",
                "value": [tcga_cancer_id]
                }
        }


class TCGARnaSeqDataSource(TCGADataSource):
    '''
    A specific implementation of the TCGA data source specific to
    RNA-seq.
    '''

    # We look for HTSeq-based counts from TCGA
    HTSEQ_SUFFIX = 'htseq.counts.gz'

    # A short name (string) which can be used as a "title" for the dataset
    PUBLIC_NAME = 'TCGA RNA-Seq'

    # A longer, more descriptive text explaining the datasource:
    DESCRIPTION = ('RNA-Seq expression data as processed by the'
        ' Genomic Data Commons'
        ' <a href="https://docs.gdc.cancer.gov/Data/Bioinformatics_Pipelines/Expression_mRNA_Pipeline/">'
        ' mRNA analysis pipeline</a>. Quantifications from this pipeline'
        ' are produced by HTSeq.'
    )

    # a string which will make it obvious where the data has come from. For example, we can use
    # this tag to name an output file produced by this class (e.g. the count matrix).
    # We also use this tag
    TAG = 'tcga-rnaseq'

    # A format-string for the annotation file
    ANNOTATION_OUTPUT_FILE = 'annotations.{tag}.{ds}.csv'

    # A format-string for the count file
    COUNT_OUTPUT_FILE = 'counts.{tag}.{ds}.hd5'

    # This list defines further filters which are specific to this class where we
    # are getting data regarding HTSeq-based RNA-seq counts. This list is in addition
    # to any other FILTER_LIST class attributes defined in parent classes. We will
    # ultimately combine them using a logical AND to create the final filter for our query
    # to the GDC API.
    RNASEQ_FILTERS = [
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
    

    # The count files include counts to non-genic features. We don't want those
    # in our final assembled count matrix
    SKIPPED_FEATURES = [
        '__no_feature', 
        '__ambiguous',
        '__too_low_aQual', 
        '__not_aligned', 
        '__alignment_not_unique'
    ]

    def __init__(self):
        super().__init__()
        self.date_str = datetime.datetime.now().strftime('%m%d%Y')

    def _create_rnaseq_query_params(self, cancer_type):
        '''
        Internal method to create the GDC-compatible parameter syntax.

        The parameter payload will dictate which data to get, which filters 
        to apply, etc.

        Returns a dict
        '''
        final_filter_list = []

        # filters to subset to the TCGA project
        final_filter_list.extend(TCGADataSource.TCGA_FILTERS)

        # a filter for this specific cancer type
        final_filter_list.append(self.create_cancer_specific_filter(cancer_type))

        # and for the specific RNA-seq data
        final_filter_list.extend(self.RNASEQ_FILTERS)

        final_filter = {
            'op': 'and',
            'content': final_filter_list
        }

        basic_fields = GDCDataSource.CASE_FIELDS
        expanded_fields = ','.join(GDCDataSource.CASE_EXPANDABLE_FIELDS)
        final_query_params = self.create_query_params(
            basic_fields,
            expand = expanded_fields,
            filters = json.dumps(final_filter)
        )
        return final_query_params


    def _download_expression_archives(self, file_uuid_list):
        '''
        Given a list of file UUIDs, download those to the local disk.
        Return the path to the downloaded archive.
        '''
        # Download the actual expression data corresponding to the aliquot metadata
        # we've been collecting
        download_params = {"ids": file_uuid_list}
        download_response = requests.post(GDCDataSource.GDC_DATA_ENDPOINT, 
            data = json.dumps(download_params), 
            headers = {"Content-Type": "application/json"}
        )
        response_head_cd = download_response.headers["Content-Disposition"]
        file_name = re.findall("filename=(.+)", response_head_cd)[0]
        fout = os.path.join('/tmp', file_name)
        with open(fout, "wb") as output_file:
            output_file.write(download_response.content)
        return fout

    def _download_tcga_cohort(self, cancer_type, data_fields):
        '''
        Handles the download of metadata and actual data for a single
        TCGA cancer type. Will return a tuple of:
        - dataframe giving the metadata (i.e. patient info)
        - count matrix 
        '''
        final_query_params = self._create_rnaseq_query_params(cancer_type)
        
        # prepare some temporary loop variables
        finished = False
        i = 0
        downloaded_archives = []

        # We have to keep a map of the fileId to the aliquot so we can properly 
        # concatenate the files later
        file_to_aliquot_mapping = {}
        annotation_df = pd.DataFrame()
        while not finished:
            logger.info('Downloading batch %d for %s...' % (i, cancer_type))

            # the records are paginated, so we have to keep track of which page we are currently requesting
            start_index = i*GDCDataSource.PAGE_SIZE
            end_index = (i+1)*GDCDataSource.PAGE_SIZE
            final_query_params.update(
                {
                    'from': start_index
                }
            )

            try:
                response = get_with_retry(
                    GDCDataSource.GDC_FILES_ENDPOINT, 
                    params = final_query_params
                )
            except Exception as ex:
                logger.info('An exception was raised when querying the GDC for'
                    ' metadata. The exception reads: {ex}'.format(ex=ex)
                )
                return

            if response.status_code == 200:
                response_json = json.loads(response.content.decode("utf-8"))
            else:
                logger.error('The response code was NOT 200, but the request'
                    ' exception was not handled.'
                )
                return

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

                # hit['cases'] is a list. To date, have only seen length of 1, 
                # and it's not clear what a greater length would mean.
                # Hence, catch this and issue an error so we can investigate
                if len(hit['cases']) > 1:
                    logger.error('Encountered an unexpected issue when iterating through the returned hits'
                        ' of a TCGA RNA-seq query. We expect the "cases" key for a hit to be of length 1,'
                        ' but this was greater. Returned data was: {k}'.format(k=json.dumps(response_json))
                    )
                    return

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
                    logger.error('Encountered an unexpected issue when iterating through the returned hits'
                        ' of a TCGA RNA-seq query. We expect that we should be able to drill-down to find a unique aliquot ID.'
                        ' The returned data was: {k}'.format(k=json.dumps(response_json))
                    )
                    return

            file_to_aliquot_mapping.update(dict(zip(file_uuid_list, aliquot_ids)))

            exposure_df = GDCDataSource.merge_with_full_record(
                data_fields['exposure'], 
                exposures, 
                aliquot_ids
            )

            demographic_df = GDCDataSource.merge_with_full_record(
                data_fields['demographic'], 
                demographics, 
                aliquot_ids
            )

            diagnoses_df = GDCDataSource.merge_with_full_record(
                data_fields['diagnosis'], 
                diagnoses, 
                aliquot_ids
            )

            # note that we keep the extra 'project_id' field in this method call. 
            # That gives us the cancer type such as "TCGA-BRCA", etc.
            project_df = GDCDataSource.merge_with_full_record(
                data_fields['project'], 
                projects, 
                aliquot_ids,
                extra_fields = ['project_id']
            )

            # Remove the extra project_id column from the exposure, demo, and diagnoses dataframes. Otherwise we get duplicated
            # columns that we have to carry around:
            exposure_df = exposure_df.drop('project_id', axis=1)
            diagnoses_df = diagnoses_df.drop('project_id', axis=1)
            demographic_df = demographic_df.drop('project_id', axis=1)

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

            # Add to the master dataframe for this cancer type
            annotation_df = pd.concat([annotation_df, ann_df], axis=0)

            # Go get the actual count data for this batch.
            downloaded_archives.append(
                self._download_expression_archives(file_uuid_list)
            )

            i += 1

            # are we done yet???
            if end_index >= total_records:
                finished = True

        logger.info('Completed looping through the batches for {ct}'.format(ct=cancer_type))

        # Merge and write the count files
        count_df = self._merge_downloaded_archives(downloaded_archives, file_to_aliquot_mapping)

        # Cleanup the downloads
        [os.remove(x) for x in downloaded_archives]

        return annotation_df, count_df


    def _merge_downloaded_archives(self, downloaded_archives, file_to_aliquot_mapping):
        '''
        Given a list of the downloaded archives, extract and merge them into a single count matrix
        '''
        logger.info('Begin merging the individual count matrix archives into a single count matrix')
        count_df = pd.DataFrame()
        tmpdir = os.path.join(self.ROOT_DIR, 'tmparchive')
        for f in downloaded_archives:
            with tarfile.open(f, 'r:gz') as tf:
                tf.extractall(path=tmpdir)
                for t in tf.getmembers():
                    if t.name.endswith(self.HTSEQ_SUFFIX):
                        # the folder has the name of the file.
                        # The prefix UUID on the basename is not useful to us.
                        file_id = t.name.split('/')[0]
                        df = pd.read_table(
                            os.path.join(tmpdir, t.path), 
                            index_col=0, 
                            header=None, 
                            names=['gene', file_to_aliquot_mapping[file_id]])
                        count_df = pd.concat([count_df, df], axis=1)

        # remove the skipped rows which don't correspond to actual gene features
        count_df = count_df.loc[~count_df.index.isin(self.SKIPPED_FEATURES)]

        # Clean up:
        shutil.rmtree(tmpdir)

        return count_df


    def prepare(self):
        '''
        Entry method for downloading and munging the TCGA RNA-seq dataset
        to a HDF5 file

        Note that creating a flat file of everything was not performant
        and created a >2Gb matrix. Instead, we organize the RNA-seq data
        hierarchically by splitting into the TCGA cancer types (e.g. TCGA-BRCA).
        Each of those is assigned to a "dataset" in the HDF5 file. Therefore,
        instead of a giant matrix we have to load each time, we can directly
        go to cancer-specific count matrices for much better performance.
        '''

        # first get all the TCGA cancer types.
        tcga_cancer_types = self.query_for_tcga_types()
        tcga_cancer_types = ['TCGA-UVM', 'TCGA-MESO']

        # Get the data dictionary, which will tell us the universe of available
        # fields and how to interpret them:
        data_fields = self.get_data_dictionary()

        total_annotation_df = pd.DataFrame()
        counts_output_path = os.path.join(
            self.ROOT_DIR,
            self.COUNT_OUTPUT_FILE.format(tag=self.TAG, ds=self.date_str)
        )
        with pd.HDFStore(counts_output_path) as hdf_out:
            for cancer_type in tcga_cancer_types:
                logger.info('Pull data for %s' % cancer_type)
                ann_df, count_df = self._download_tcga_cohort(cancer_type, data_fields)
                total_annotation_df = pd.concat([total_annotation_df, ann_df], axis=0)

                # save the counts to a cancer-specific dataset. Store each
                # dataset in a cancer-specific group. On testing, this seemed
                # to be a bit faster for recall than keeping all the dataframes
                # as datasets in the root group
                group_id = (
                    self._create_python_compatible_tcga_id(cancer_type) + '/ds')
                hdf_out.put(group_id, count_df)
                logger.info('Added the {ct} matrix to the HDF5'
                    ' count matrix'.format(ct=cancer_type)
                )

        # Write all the metadata to a file
        ann_output_path = os.path.join(
            self.ROOT_DIR,
            self.ANNOTATION_OUTPUT_FILE.format(tag = self.TAG, ds=self.date_str)
        )
        total_annotation_df.to_csv(
            ann_output_path, 
            sep=',', 
            index_label = 'id'
        )
        logger.info('The metadata/annnotation file for your TCGA RNA-seq data'
            'is available at {p}'.format(p=ann_output_path))
        

class MiniTCGARnaSeqDataSource(TCGARnaSeqDataSource):
    '''
    A subset of the TCGARnaSeqDataSource for only TCGA-UVM
    and TCGA-MESO. 
    '''

    # a string which will make it obvious where the data has come from. For example, we can use
    # this tag to name an output file produced by this class (e.g. the count matrix).
    # We also use this tag
    TAG = 'mini-tcga-rnaseq'

    FILTER_LIST = [
        {
            "op": "in",
            "content":{
                "field": "files.cases.project.project_id",
                "value": ["TCGA-UVM", "TCGA-MESO"]
                }
        }
    ]