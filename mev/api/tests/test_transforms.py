import uuid
import os
import json
import unittest.mock as mock
from itertools import chain

from rest_framework.exceptions import ValidationError

from api.models import Resource
from api.tests.base import BaseAPITestCase

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
        self.resource.path = fp

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