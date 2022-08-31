import uuid
import os
import json
import unittest.mock as mock
from itertools import chain

from rest_framework.exceptions import ValidationError

from api.models import Resource
from api.tests.base import BaseAPITestCase
from api.tests.test_helpers import cleanup_resource_file, \
    associate_file_with_resource

from api.data_transformations.network_transforms import subset_PANDA_net

class ResourceTransformTests(BaseAPITestCase):

    def setUp(self):

        self.TESTDIR = os.path.join(
            os.path.dirname(__file__),
            'resource_contents_test_files'    
        )
        # get an example from the database:
        self.resource = Resource.objects.all()[0]
        
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

        cleanup_resource_file(self.resource)

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

        cleanup_resource_file(self.resource)