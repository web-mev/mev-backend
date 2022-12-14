import os
import unittest.mock as mock
from itertools import chain

from constants import MATRIX_KEY, \
    TSV_FORMAT, \
    FEATURE_TABLE_KEY, \
    JSON_FILE_KEY, \
    JSON_FORMAT

from api.models import Resource
from api.tests.base import BaseAPITestCase
from api.tests.test_helpers import associate_file_with_resource

from api.data_transformations.network_transforms import subset_PANDA_net
from api.data_transformations.heatmap_transforms import heatmap_reduce

class ResourceTransformTests(BaseAPITestCase):

    def setUp(self):

        self.TESTDIR = os.path.join(
            os.path.dirname(__file__),
            'resource_contents_test_files'    
        )
        # get an example from the database:
        self.resource = Resource.objects.all()[0]

    def test_heatmap_hcl_transform_case(self):
        fp = os.path.join(self.TESTDIR, 'heatmap_hcl_test.tsv')
        self.resource.resource_type = MATRIX_KEY
        self.resource.file_format = TSV_FORMAT
        self.resource.save()
        associate_file_with_resource(self.resource, fp)
        query_params = {
            'mad_n': 5
        }
        result = heatmap_reduce(self.resource, query_params)
        expected_row_ordering = ['g3','g1','g2','g6','g4']
        self.assertEqual(expected_row_ordering, [x['rowname'] for x in result])
        expected_col_ordering = ['s1','s3','s5','s2','s4','s6']
        self.assertEqual(expected_col_ordering, [x for x in result[0]['values']])

    def test_heatmap_hcl_bad_resource_type(self):
        '''
        Test that we appropriately warn if the heatmap clustering function
        is called for an unacceptable resource type
        '''
        # test that it works for an all-numeric FT:
        fp = os.path.join(self.TESTDIR, 'json_array_file.json')
        self.resource.resource_type = JSON_FILE_KEY
        self.resource.file_format = JSON_FORMAT
        self.resource.save()
        associate_file_with_resource(self.resource, fp)
        query_params = {
            'mad_n': 5
        }
        with self.assertRaisesRegex(Exception, 'Not an acceptable resource type'):
            heatmap_reduce(self.resource, query_params)

    def test_heatmap_hcl_warns_non_numeric(self):
        '''
        Test that we appropriately warn if the heatmap clustering function
        can't work due to a non-numeric entry in the table. Since we can
        technically have feature tables that are all numeric, they CAN
        work on some types. However, we need to catch and warn attempts
        where we can't perform the calculation. 
        
        An example would be an output from LIONESS--
        it's a feature table since each row concerns the weights
        (e.g. to transcription factors) for each gene. It's NOT
        a matrix since the columns are not technically observations
        (samples).
        '''
        # test that it works for an all-numeric FT:
        fp = os.path.join(self.TESTDIR, 'heatmap_hcl_test.tsv')
        self.resource.resource_type = FEATURE_TABLE_KEY
        self.resource.file_format = TSV_FORMAT
        self.resource.save()
        associate_file_with_resource(self.resource, fp)
        query_params = {
            'mad_n': 5
        }
        result = heatmap_reduce(self.resource, query_params)
        expected_row_ordering = ['g3','g1','g2','g6','g4']
        self.assertEqual(expected_row_ordering, [x['rowname'] for x in result])
        expected_col_ordering = ['s1','s3','s5','s2','s4','s6']
        self.assertEqual(expected_col_ordering, [x for x in result[0]['values']])

        # now test that it fails for a table with non-numeric
        fp = os.path.join(self.TESTDIR, 'table_with_string_field.tsv')
        self.resource.resource_type = FEATURE_TABLE_KEY
        self.resource.file_format = TSV_FORMAT
        self.resource.save()
        associate_file_with_resource(self.resource, fp)
        query_params = {
            'mad_n': 5
        }
        with self.assertRaisesRegex(Exception, 'Could not calculate'):
            heatmap_reduce(self.resource, query_params)

    def test_panda_subset_transform_case(self):
        fp = os.path.join(self.TESTDIR, 'example_panda_output.tsv')
        associate_file_with_resource(self.resource, fp)

        expected_result = {
            "initial_axis": 0,
            "nodes": [
                {
                "ENSG_7": {
                    "axis": 0,
                    "children": [
                    {
                        "TF_5": 99
                    },
                    {
                        "TF_3": 98
                    }
                    ]
                }
                },
                {
                "ENSG_6": {
                    "axis": 0,
                    "children": [
                    {
                        "TF_5": 96
                    },
                    {
                        "TF_1": 87
                    }
                    ]
                }
                },
                {
                "TF_1": {
                    "axis": 1,
                    "children": [
                    {
                        "ENSG_2": 97
                    },
                    {
                        "ENSG_6": 87
                    }
                    ]
                }
                },
                {
                "TF_5": {
                    "axis": 1,
                    "children": [
                    {
                        "ENSG_7": 99
                    },
                    {
                        "ENSG_6": 96
                    }
                    ]
                }
                },
                {
                "TF_3": {
                    "axis": 1,
                    "children": [
                    {
                        "ENSG_7": 98
                    },
                    {
                        "ENSG_10": 97
                    }
                    ]
                }
                }
            ]
        }
        expected_nodes = ['ENSG_6', 'ENSG_7', 'TF_1', 'TF_3', 'TF_5']
        query_params = {
            'maxdepth': 2,
            'children': 2,
            'axis': 0
        }
        result = subset_PANDA_net(self.resource, query_params)
        nodes = list(set(chain.from_iterable([x.keys() for x in result['nodes']])))
        self.assertCountEqual(expected_nodes, nodes)

        # # check that incomplete query parameters raise an exception:
        # # missing maxdepth
        query_params = {
            'children': 2,
            'axis': 0
        }
        with self.assertRaisesRegex(Exception, 'maxdepth'):
            subset_PANDA_net(self.resource, query_params)

        # maxdepth should be a positive integer. Here it's negative
        query_params = {
            'maxdepth': -2,
            'children': 2,
            'axis': 0
        }
        with self.assertRaisesRegex(Exception, 'not a positive integer'):
            subset_PANDA_net(self.resource, query_params)

        # axis should be 0 or 1
        query_params = {
            'maxdepth': 2,
            'children': 2,
            'axis': 3
        }
        with self.assertRaisesRegex(Exception, 'must be 0 or 1'):
            subset_PANDA_net(self.resource, query_params)

        

    def test_panda_subset_by_genes(self):
        fp = os.path.join(self.TESTDIR, 'example_panda_output.tsv')
        associate_file_with_resource(self.resource, fp)

        expected_result = {
            "initial_axis": 0,
            "nodes": [
                {
                "ENSG_1": {
                    "axis": 0,
                    "children": [
                    {
                        "TF_2": 80
                    },
                    {
                        "TF_4": 87
                    }
                    ]
                }
                },
                {
                "ENSG_9": {
                    "axis": 0,
                    "children": [
                    {
                        "TF_7": 68
                    },
                    {
                        "TF_4": 73
                    }
                    ]
                }
                },
                {
                "TF_2": {
                    "axis": 1,
                    "children": [
                    {
                        "ENSG_1": 80
                    },
                    {
                        "ENSG_4": 95
                    }
                    ]
                }
                },
                {
                "TF_4": {
                    "axis": 1,
                    "children": [
                    {
                        "ENSG_1": 87
                    },
                    {
                        "ENSG_10": 91
                    }
                    ]
                }
                },
                {
                "TF_7": {
                    "axis": 1,
                    "children": [
                    {
                        "ENSG_5": 89
                    },
                    {
                        "ENSG_2": 90
                    }
                    ]
                }
                }
            ]
        }
        expected_nodes = ['ENSG_1', 'ENSG_9', 'TF_2', 'TF_4', 'TF_7']
        query_params = {
            'maxdepth': 2,
            'children': 2,
            'axis': 0,
            'initial_nodes': 'ENSG_1,ENSG_9'
        }
        result = subset_PANDA_net(self.resource, query_params)
        nodes = list(set(chain.from_iterable([x.keys() for x in result['nodes']])))
        self.assertCountEqual(expected_nodes, nodes)

        # test with a bad gene
        query_params = {
            'maxdepth': 2,
            'children': 2,
            'axis': 0,
            'initial_nodes': 'ENSG_1,ENSG_666'
        }
        with self.assertRaisesRegex(Exception, 'ENSG_666'):
            subset_PANDA_net(self.resource, query_params)

        # test with a bad delimiter
        query_params = {
            'maxdepth': 2,
            'children': 2,
            'axis': 0,
            'initial_nodes': 'ENSG_1:ENSG_666'
        }
        with self.assertRaisesRegex(Exception, 'ENSG_1:ENSG_666'):
            subset_PANDA_net(self.resource, query_params)

        # test other direction (TFs, axis=1), but keep (by accident)
        # a query on the genes
        query_params = {
            'maxdepth': 2,
            'children': 2,
            'axis': 1,
            'initial_nodes': 'ENSG_1,ENSG_9'
        }
        with self.assertRaisesRegex(Exception, 'ENSG_1'):
            result = subset_PANDA_net(self.resource, query_params)

        # now try a correct query for the TFs
        query_params = {
            'maxdepth': 2,
            'children': 2,
            'axis': 1,
            'initial_nodes': 'TF_2,TF_4'
        }
        result = subset_PANDA_net(self.resource, query_params)
        nodes = list(set(chain.from_iterable([x.keys() for x in result['nodes']])))
        expected_nodes = ['TF_2', 'TF_4', 'ENSG_1', 'ENSG_4', 'ENSG_10']
        self.assertCountEqual(expected_nodes, nodes)

        # test that too many requested nodes causes an error
        # The 0 axis has 40 entries. If it had fewer entries (e.g. 10),
        # then the top N function would just select 10 if given a
        # large number
        query_params = {
            'maxdepth': 3,
            'children': 30,
            'axis': 0
        }
        with self.assertRaisesRegex(Exception, 'choose fewer'):
            result = subset_PANDA_net(self.resource, query_params)

        