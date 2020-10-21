import unittest
import numpy as np
import pandas as pd

from resource_types import RESOURCE_MAPPING

class TestResourceTypes(unittest.TestCase):    
    
    def test_all_resources_have_acceptable_extensions(self):
        '''
        If any of the resource types are missing the ACCEPTABLE_EXTENSIONS
        key, then this test will raise an AttributeError
        '''
        for k,v in RESOURCE_MAPPING.items():
            v.ACCEPTABLE_EXTENSIONS

class TestTableResource(unittest.TestCase):

    def test_save_in_standardized_format(self):

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
        new_path, new_name = mtx_type.save_in_standardized_format(path, 'test_matrix.csv')
        
        self.assertEqual('/tmp/test_matrix.tsv', new_path)
        self.assertEqual('test_matrix.tsv', new_name)

        # check that they have the same content:
        reloaded_df = pd.read_table(new_path, index_col=0)
        self.assertTrue(reloaded_df.equals(df))