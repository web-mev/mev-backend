import unittest
import unittest.mock as mock
import numpy as np
import pandas as pd
import uuid
import os

from django.conf import settings

from constants import TSV_FORMAT, \
    PARENT_OP_KEY, \
    FEATURE_SET_KEY, \
    OBSERVATION_SET_KEY, \
    RESOURCE_KEY

from resource_types import RESOURCE_MAPPING, \
    format_is_acceptable_for_type
from resource_types.base import DataResource
from resource_types.table_types import TableResource

class TestResourceTypes(unittest.TestCase):    
    
    def test_all_resources_have_acceptable_formats(self):
        '''
        If any of the resource types are missing the ACCEPTABLE_FORMATS
        attribute, then this test will raise an AttributeError
        '''
        for k,v in RESOURCE_MAPPING.items():
            v.ACCEPTABLE_FORMATS

    def test_all_resources_have_standard_formats(self):
        '''
        If any of the resource types are missing the STANDARD_FORMAT
        attribute, then this test will raise an AttributeError
        '''
        for k,v in RESOURCE_MAPPING.items():
            v.STANDARD_FORMAT

class TestBaseDataResource(unittest.TestCase):

    def test_metadata_setup(self):
        d = DataResource()
        d.setup_metadata()
        self.assertIsNone(d.metadata.get(PARENT_OP_KEY))
        self.assertIsNone(d.metadata.get(FEATURE_SET_KEY))
        self.assertIsNone(d.metadata.get(OBSERVATION_SET_KEY))
        self.assertIsNone(d.metadata.get(RESOURCE_KEY))

class TestTableResource(unittest.TestCase):

    @mock.patch('resource_types.table_types.uuid')
    def test_save_in_standardized_format(self, mock_uuid):
        '''
        Test that the 'reformatting' of the CSV-format to our
        standard TSV format works as expected.
        '''
        u = uuid.uuid4()
        mock_uuid.uuid4.return_value = u

        # create some temp file written in CSV format (which is not the internal
        # standard we want.)
        columns = ['colA', 'colB', 'colC']
        rows = ['geneA', 'geneB', 'geneC']
        values = np.arange(9).reshape((3,3))
        expected_return = {
            'colA': {'geneA':0, 'geneB':3, 'geneC':6},
            'colB': {'geneA':1, 'geneB':4, 'geneC':7},
            'colC': {'geneA':2, 'geneB':5, 'geneC':8}
        }
        df = pd.DataFrame(values, index=rows, columns=columns)
        path = '/tmp/test_matrix.csv'
        df.to_csv(path, sep=',')

        mtx_class = RESOURCE_MAPPING['MTX']
        mtx_type = mtx_class()
        new_path = mtx_type.save_in_standardized_format(path, 'csv')

        self.assertTrue(os.path.dirname(new_path) == settings.VALIDATION_TMP_DIR)

        # check that they have the same content:
        reloaded_df = pd.read_table(new_path, index_col=0)
        self.assertTrue(reloaded_df.equals(df))

    def test_save_in_standardized_format_case2(self):
        '''
        If the file is already in our standard format, check that we 
        just get back the same path and name for the resource.
        '''
        # create some temp file written in TSV format (which IS the internal
        # standard we want.)
        columns = ['colA', 'colB', 'colC']
        rows = ['geneA', 'geneB', 'geneC']
        values = np.arange(9).reshape((3,3))
        expected_return = {
            'colA': {'geneA':0, 'geneB':3, 'geneC':6},
            'colB': {'geneA':1, 'geneB':4, 'geneC':7},
            'colC': {'geneA':2, 'geneB':5, 'geneC':8}
        }
        df = pd.DataFrame(values, index=rows, columns=columns)
        orig_name = 'test_matrix.tsv'
        path = os.path.join('/tmp', orig_name)
        df.to_csv(path, sep='\t')

        mtx_class = RESOURCE_MAPPING['MTX']
        mtx_type = mtx_class()
        self.assertTrue(TSV_FORMAT == mtx_type.STANDARD_FORMAT)
        new_path = mtx_type.save_in_standardized_format(path, TSV_FORMAT)

        self.assertEqual(path, new_path)

        # check that they have the same content:
        reloaded_df = pd.read_table(new_path, index_col=0)
        self.assertTrue(reloaded_df.equals(df))

    def test_case_insensitive_file_format(self):
        '''
        Checks that the reader type (e.g. read_csv, read_table, etc.)
        does not depend on the case of the passed file format
        '''
        reader = TableResource().get_reader('/some/dummy/path.txt', 'TSV')
        self.assertIsNotNone(reader)
        reader = TableResource().get_reader('/some/dummy/path.txt', 'TsV')
        self.assertIsNotNone(reader)

class TestResourcePkgFunctions(unittest.TestCase):

    @mock.patch('resource_types.get_acceptable_formats')
    def test_format_consistent_function(self, mock_get_acceptable_formats):

        mock_get_acceptable_formats.return_value = ['tsv','csv']

        # an unacceptable format:
        self.assertFalse(format_is_acceptable_for_type('abc', ''))

        # tests an exact match to the accepted formats
        self.assertTrue(format_is_acceptable_for_type('csv', ''))

        # tests the case-insensitivity
        self.assertTrue(format_is_acceptable_for_type('TsV', ''))

        # Test an empty string when we have no allowance for wildcards
        self.assertFalse(format_is_acceptable_for_type('', ''))

        # Add a wildcard and check that the bogus format is fine
        mock_get_acceptable_formats.return_value = ['tsv','csv', '*']
        self.assertTrue(format_is_acceptable_for_type('abc', ''))

        # Test an empty string for format is ok for wildcards
        self.assertTrue(format_is_acceptable_for_type('', ''))

        mock_get_acceptable_formats.side_effect = KeyError('xyz')
        with self.assertRaises(KeyError):
            format_is_acceptable_for_type('abc', 'garbage')
