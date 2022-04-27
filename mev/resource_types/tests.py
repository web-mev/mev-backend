import unittest
import unittest.mock as mock
import numpy as np
import pandas as pd
import uuid
import os

from resource_types import RESOURCE_MAPPING, \
    extension_is_consistent_with_type

class TestResourceTypes(unittest.TestCase):    
    
    def test_all_resources_have_acceptable_extensions(self):
        '''
        If any of the resource types are missing the ACCEPTABLE_EXTENSIONS
        key, then this test will raise an AttributeError
        '''
        for k,v in RESOURCE_MAPPING.items():
            v.ACCEPTABLE_EXTENSIONS

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
        new_path, new_name = mtx_type.save_in_standardized_format(path, 'test_matrix.csv', 'csv')
        
        self.assertEqual('/tmp/{x}'.format(x=str(u)), new_path)
        self.assertEqual('test_matrix.tsv', new_name)

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
        new_path, new_name = mtx_type.save_in_standardized_format(path, 'test_matrix.tsv', 'tsv')
        
        self.assertEqual(path, new_path)
        self.assertEqual(orig_name, new_name)

        # check that they have the same content:
        reloaded_df = pd.read_table(new_path, index_col=0)
        self.assertTrue(reloaded_df.equals(df))

class TestResourcePkgFunctions(unittest.TestCase):

    @mock.patch('resource_types.get_acceptable_extensions')
    def test_extension_consistent_function(self, mock_get_acceptable_extensions):

        mock_get_acceptable_extensions.return_value = ['tsv','csv']

        # an unacceptable extension:
        self.assertFalse(extension_is_consistent_with_type('abc', ''))

        # tests an exact match to the accepted extensions
        self.assertTrue(extension_is_consistent_with_type('csv', ''))

        # tests the case-insensitivity
        self.assertTrue(extension_is_consistent_with_type('TsV', ''))

        # Test an empty string when we have no allowance for wildcards
        self.assertFalse(extension_is_consistent_with_type('', ''))

        # Add a wildcard and check that the bogus extension is fine
        mock_get_acceptable_extensions.return_value = ['tsv','csv', '*']
        self.assertTrue(extension_is_consistent_with_type('abc', ''))

        # Test an empty string for extension is ok for wildcards
        self.assertTrue(extension_is_consistent_with_type('', ''))

        mock_get_acceptable_extensions.side_effect = KeyError('xyz')
        with self.assertRaisesRegex(Exception, "type 'xyz' is not among the accepted types"):
            extension_is_consistent_with_type('abc', 'garbage')
