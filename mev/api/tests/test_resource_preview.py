import unittest
import os

import pandas as pd
import numpy as np

from resource_types import RESOURCE_MAPPING

TESTDIR = os.path.dirname(__file__)
TESTDIR = os.path.join(TESTDIR, 'resource_validation_test_files')

class TestResourcePreview(unittest.TestCase):
    '''
    Tests that the resource previews return the proper
    format.
    '''

    def test_table_preview(self):
        '''
        Tests that the returned preview has the expected format.
        '''

        columns = ['colA', 'colB', 'colC']
        rows = ['geneA', 'geneB', 'geneC']
        values = np.arange(9).reshape((3,3))
        expected_return = {
            'colA': {'geneA':0, 'geneB':3, 'geneC':6},
            'colB': {'geneA':1, 'geneB':4, 'geneC':7},
            'colC': {'geneA':2, 'geneB':5, 'geneC':8}
        }
        df = pd.DataFrame(values, index=rows, columns=columns)
        path = os.path.join('/tmp', 'test_preview_matrix.tsv')
        df.to_csv(path, sep='\t')

        mtx_class = RESOURCE_MAPPING['MTX']
        mtx_type = mtx_class()
        contents = mtx_type.get_contents(path)
        self.assertTrue(df.equals(contents))

    def test_empty_table_preview(self):
        '''
        In principle, the resource should be validated so this should
        never happen.  But just in case, we test what happens if the table
        is empty or has a parsing error
        '''
        path = os.path.join(TESTDIR, 'test_empty.tsv')

        mtx_class = RESOURCE_MAPPING['MTX']
        mtx_type = mtx_class()
        with self.assertRaises(Exception):
            mtx_type.get_contents(path)