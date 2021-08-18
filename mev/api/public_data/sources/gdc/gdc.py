import json
from os import stat
import requests

import pandas as pd

from api.public_data.sources.base import PublicDataSource

class GDCDataSource(PublicDataSource):
    
    GDC_FILES_ENDPOINT = "https://api.gdc.cancer.gov/files"
    GDC_DATA_ENDPOINT = "https://api.gdc.cancer.gov/data"
    GDC_DICTIONARY_ENDPOINT = 'https://api.gdc.cancer.gov/v0/submission/_dictionary/{attribute}?format=json'

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
    # The query params shown here are quite general-- the derived classes should specify
    # a filter to query for the data of interest (e.g. data types, experimental strategy)
    QUERY_PARAMS = {
        "fields": ','.join(FIELDS),
        "format": "JSON",
        # cast this int as a string since it becomes a url param:
        "size": str(PAGE_SIZE),
        "expand": ','.join(EXPANDABLE_FIELDS)
    }

    def download_and_prep_dataset(self):
        '''
        Used to periodically pull data from the GDC 
        '''
        raise NotImplementedError('You must implement this method in a child class.')

    @staticmethod
    def merge_with_full_record(full_record, returned_data, aliquot_ids, extra_fields=None):
        '''
        This method is used to merge the actual returned data with a dictionary that has the
        universe of possible data fields. The result is a merged data structure that combines
        the returned data with that full set of potential fields.

        More explanation:

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

    def get_data_dictiontary(self):
        '''
        The GDC defines a data schema which we query here. This gives the universe
        of data fields, which are used by children classes.
        '''

        # When querying the data dictionary, we also get extraneous fields
        # we don't care about. Add those to this list:
        IGNORED_PROPERTIES = [
            'cases',
            'state',
            'type',
            'updated_datetime',
            'created_datetime',
            'id',
            'submitter_id',
            'releasable',
            'released',
            'intended_release_date',
            'batch_id',
            'programs'
        ]

        # Rather than getting EVERYTHING, we only query which fields are
        # available within these general categories:
        ATTRIBUTES = [
            'demographic',
            'diagnosis',
            'exposure',
            'project'
        ]

        d = {}
        for attr in ATTRIBUTES:
            property_list = []
            url = self.GDC_DICTIONARY_ENDPOINT.format(attribute = attr)
            response = requests.get(url)
            j = response.json()
            properties = j['properties']

            for k in properties.keys():
                if k in IGNORED_PROPERTIES:
                    continue
                try:
                    description = properties[k]['description']
                except KeyError as ex:
                    description = None
                property_list.append({
                    'field': k,
                    'description': description
                })
            d[attr] = property_list
        return d