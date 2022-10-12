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

from data_structures.observation import Observation

from resource_types import RESOURCE_MAPPING, \
    format_is_acceptable_for_type
from resource_types.base import DataResource
from resource_types.table_types import TableResource, ElementTable

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

    def test_case_insensitive_file_format(self):
        '''
        Checks that the reader type (e.g. read_csv, read_table, etc.)
        does not depend on the case of the passed file format
        '''
        reader = TableResource().get_reader('TSV')
        self.assertIsNotNone(reader)
        reader = TableResource().get_reader('TsV')
        self.assertIsNotNone(reader)

class TestResourceElementTable(unittest.TestCase):

    def test_returns_empty_metadata_from_large_table(self):
        '''
        This tests that we handle exceptionally large annotation tables which cause the 
        server to become unresponsive.

        Related to a bug where a user incorrectly takes a large expression matrix (e.g. 50k x 500)
        and attempts to set the resource_type to an annotation table. The process gets hung up
        on trying to create the dictionary of attributes to values necessary to create an ObservationSet.

        In the case of a very large table, we simply return empty metadata
        '''

        # First test that it works in the case of a small table
        samples = ['A','B','C']
        df = pd.DataFrame(
            {
                'age':[1,2,3], 
                'sex':['F','F','M']
            },
            index=samples
        )
        t = ElementTable()
        t.table = df
        observation_list = t.prep_metadata(Observation)
        self.assertTrue(len(observation_list) == 3)

        # now test the huge one
        max_observations = ElementTable.MAX_OBSERVATIONS
        max_features = ElementTable.MAX_FEATURES

        nrows = max_observations + 1
        ncols = 10
        rownames = ['r%d' % x for x in range(nrows)]
        colnames = ['c%d' % x for x in range(ncols)]
        df = pd.DataFrame(np.random.randint(0,100, size=(nrows, ncols)), index=rownames, columns=colnames)
        t.table = df
        observation_list = t.prep_metadata(Observation)
        self.assertCountEqual(observation_list, [])
        
        nrows = 10
        ncols = max_features + 1
        rownames = ['r%d' % x for x in range(nrows)]
        colnames = ['c%d' % x for x in range(ncols)]
        df = pd.DataFrame(np.random.randint(0,100, size=(nrows, ncols)), index=rownames, columns=colnames)
        t.table = df
        observation_list = t.prep_metadata(Observation)
        self.assertCountEqual(observation_list, [])

        nrows = max_observations + 1
        ncols = max_features + 1
        rownames = ['r%d' % x for x in range(nrows)]
        colnames = ['c%d' % x for x in range(ncols)]
        df = pd.DataFrame(np.random.randint(0,100, size=(nrows, ncols)), index=rownames, columns=colnames)
        t.table = df
        observation_list = t.prep_metadata(Observation)
        self.assertCountEqual(observation_list, [])


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
