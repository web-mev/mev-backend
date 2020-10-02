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
            'columns': columns,
            'rows': rows,
            'values': values.tolist()
        }
        df = pd.DataFrame(values, index=rows, columns=columns)
        path = os.path.join('/tmp', 'test_preview_matrix.tsv')
        df.to_csv(path, sep='\t')

        mtx_class = RESOURCE_MAPPING['MTX']
        mtx_type = mtx_class()
        preview = mtx_type.get_contents(path)
        self.assertDictEqual(preview, expected_return)

    def test_table_preview_with_limit(self):
        '''
        Tests that the returned preview has the expected format.
        Here, we limit the result to 2 entries
        '''

        columns = ['colA', 'colB', 'colC']
        rows = ['geneA', 'geneB', 'geneC']
        values = np.arange(9).reshape((3,3))
        expected_return = {
            'columns': columns, # columns don't change in a subset for rows
            'rows': rows[:2],
            'values': values[:2,:].tolist()
        }
        df = pd.DataFrame(values, index=rows, columns=columns)
        path = os.path.join('/tmp', 'test_preview_matrix.tsv')
        df.to_csv(path, sep='\t')

        mtx_class = RESOURCE_MAPPING['MTX']
        mtx_type = mtx_class()
        preview = mtx_type.get_contents(path, limit=2)
        self.assertDictEqual(preview, expected_return)

    def test_empty_table_preview(self):
        '''
        In principle, the resource should be validated so this should
        never happen.  But just in case, we test what happens if the table
        is empty or has a parsing error
        '''
        path = os.path.join(TESTDIR, 'test_empty.tsv')

        mtx_class = RESOURCE_MAPPING['MTX']
        mtx_type = mtx_class()
        preview = mtx_type.get_contents(path)
        self.assertTrue('error' in preview)