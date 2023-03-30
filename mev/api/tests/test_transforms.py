from operator import index
import os
import unittest.mock as mock
import json
from itertools import chain

import pandas as pd

from django.conf import settings

from constants import MATRIX_KEY, \
    TSV_FORMAT, \
    FEATURE_TABLE_KEY, \
    JSON_FILE_KEY, \
    JSON_FORMAT

from exceptions import ParseException

from resource_types import get_resource_type_instance

from api.models import Resource
from api.tests.base import BaseAPITestCase
from api.tests.test_helpers import associate_file_with_resource

from api.data_transformations.network_transforms import subset_PANDA_net
from api.data_transformations.heatmap_transforms import heatmap_reduce, \
    heatmap_cluster, \
    perform_clustering
from api.data_transformations.volcano_plot_transforms import volcano_subset


class ResourceTransformTests(BaseAPITestCase):

    def setUp(self):

        self.TESTDIR = os.path.join(
            os.path.dirname(__file__),
            'resource_contents_test_files'    
        )
        # get an example from the database:
        self.resource = Resource.objects.all()[0]

    def test_clustering_function(self):
        '''
        Tests the clustering function on the entire matrix
        '''
        fp = os.path.join(self.TESTDIR, 'heatmap_hcl_test.tsv')
        df = pd.read_table(fp, index_col=0)
        resource_type_instance = get_resource_type_instance(MATRIX_KEY)
        result = perform_clustering(df, 'ward', 'euclidean', resource_type_instance)
        expected_row_ordering = ['g5','g1','g3','g6','g2','g4']
        self.assertEqual(expected_row_ordering, [x['rowname'] for x in result])
        expected_col_ordering = ['s1','s3','s5','s2','s4','s6']
        self.assertEqual(expected_col_ordering, [x for x in result[0]['values']])

    def test_clustering_function_on_empty(self):
        '''
        Tests the clustering function on a rowname filter that
        returns no records
        '''
        fp = os.path.join(self.TESTDIR, 'heatmap_hcl_test.tsv')
        self.resource.resource_type = MATRIX_KEY
        self.resource.file_format = TSV_FORMAT
        self.resource.save()
        associate_file_with_resource(self.resource, fp)
        df = pd.read_table(fp, index_col=0)
        resource_type_instance = get_resource_type_instance(MATRIX_KEY)

        query_params = {
            # This will cause an empty dataframe since there are no rows
            # with that gene symbol
            settings.ROWNAME_FILTER: '[in]:ABC'
        }
        # note that we don't do df.loc['g1'] since that creates a pd.Series.
        # instead, we rely on the actual function that filters the dataframe
        # which returns a single-row dataframe instead:
        resource_type_instance.get_contents(self.resource, query_params)
        df = resource_type_instance.table
        # create an empty dataframe to see how it handles that
        result = perform_clustering(df, 'ward', 'euclidean', resource_type_instance)
        self.assertTrue(result == [])

    def test_clustering_function_single_record(self):
        '''
        Tests the clustering function on a single gene
        '''
        fp = os.path.join(self.TESTDIR, 'heatmap_hcl_test.tsv')
        self.resource.resource_type = MATRIX_KEY
        self.resource.file_format = TSV_FORMAT
        self.resource.save()
        associate_file_with_resource(self.resource, fp)
        df = pd.read_table(fp, index_col=0)
        resource_type_instance = get_resource_type_instance(MATRIX_KEY)

        query_params = {
            settings.ROWNAME_FILTER: f'[in]:g1'
        }
        # note that we don't do df.loc['g1'] since that creates a pd.Series.
        # instead, we rely on the actual function that filters the dataframe
        # which returns a single-row dataframe instead:
        resource_type_instance.get_contents(self.resource, query_params)
        df = resource_type_instance.table
        result = perform_clustering(df, 'ward', 'euclidean', resource_type_instance)
        self.assertTrue(len(result) == 1)
        self.assertTrue(result[0]['rowname'] == 'g1')

    @mock.patch('api.data_transformations.heatmap_transforms.perform_clustering')
    def test_heatmap_cluster_transform_case1(self, mock_perform_clustering):
        '''
        Note that we don't test the clustering function itself-- 
        only the call TO that function
        '''
        fp = os.path.join(self.TESTDIR, 'heatmap_hcl_test.tsv')
        df = pd.read_table(fp, index_col=0)
        keep_genes = 'g1,g2,g3,g4,g6'
        df = df.loc[keep_genes.split(',')]

        self.resource.resource_type = MATRIX_KEY
        self.resource.file_format = TSV_FORMAT
        self.resource.save()
        associate_file_with_resource(self.resource, fp)
        query_params = {
            'metric': 'euclidean',
            'transform-name': 'blah',
            settings.ROWNAME_FILTER: f'[in]:{keep_genes}' # leaves out g5
        }
        heatmap_cluster(self.resource, query_params)
        args, kwargs = mock_perform_clustering.call_args
        passed_df = args[0]
        passed_method = args[1]
        passed_metric = args[2]
        self.assertTrue((passed_df == df).all().all())
        self.assertTrue(passed_method == 'ward')
        self.assertTrue(passed_metric == 'euclidean')
        self.assertTrue(kwargs == {})

    @mock.patch('api.data_transformations.heatmap_transforms.perform_clustering')
    def test_heatmap_cluster_transform_case2(self, mock_perform_clustering):
        '''
        Here, we pass an extra query param which should cause a problem
        '''
        fp = os.path.join(self.TESTDIR, 'heatmap_hcl_test.tsv')
        df = pd.read_table(fp, index_col=0)
        keep_genes = 'g1,g2,g3,g4,g6'
        df = df.loc[keep_genes.split(',')]

        self.resource.resource_type = MATRIX_KEY
        self.resource.file_format = TSV_FORMAT
        self.resource.save()
        associate_file_with_resource(self.resource, fp)
        query_params = {
            'metric': 'euclidean',
            'EXTRA': 'foo', # <-- BAD
            'transform-name': 'blah',
            settings.ROWNAME_FILTER: f'[in]:{keep_genes}' # leaves out g5
        }
        with self.assertRaisesRegex(ParseException, 'EXTRA'):
            heatmap_cluster(self.resource, query_params)

    @mock.patch('api.data_transformations.heatmap_transforms.perform_clustering')
    def test_heatmap_cluster_transform_case3(self, mock_perform_clustering):
        '''
        Here, we pass a gene/feature filter that has no items
        '''
        fp = os.path.join(self.TESTDIR, 'heatmap_hcl_test.tsv')
        empty_df = pd.DataFrame(columns=['s1','s2','s3','s4','s5','s6'])

        self.resource.resource_type = MATRIX_KEY
        self.resource.file_format = TSV_FORMAT
        self.resource.save()
        associate_file_with_resource(self.resource, fp)
        query_params = {
            'metric': 'euclidean',
            'transform-name': 'blah',
            settings.ROWNAME_FILTER: f'[in]:'
        }
        heatmap_cluster(self.resource, query_params)
        args, kwargs = mock_perform_clustering.call_args
        passed_df = args[0]
        passed_method = args[1]
        passed_metric = args[2]
        self.assertTrue((passed_df == empty_df).all().all())
        self.assertTrue(passed_method == 'ward')
        self.assertTrue(passed_metric == 'euclidean')
        self.assertTrue(kwargs == {})

    def test_heatmap_cluster_bad_resource_type(self):
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
        query_params = {'transform-name': 'foo'}
        with self.assertRaisesRegex(Exception, 'Not an acceptable resource type'):
            heatmap_cluster(self.resource, query_params)

    def test_heatmap_reduce_transform_case(self):
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

    def test_heatmap_reduce_bad_resource_type(self):
        '''
        Test that we appropriately warn if the heatmap reduce function
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

    def test_heatmap_reduce_warns_non_numeric(self):
        '''
        Test that we appropriately warn if the heatmap reduce function
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

    def test_volcano_subset(self):
        '''
        Test that the volcano subset transform works as
        expected
        '''
        # test that it works for an all-numeric FT:
        fp = os.path.join(self.TESTDIR, 'demo_deseq_table_2.tsv')
        self.resource.resource_type = FEATURE_TABLE_KEY
        self.resource.file_format = TSV_FORMAT
        self.resource.save()
        associate_file_with_resource(self.resource, fp)
        query_params = {
            'pval': 0.03,
            'lfc': 0.5
        }
        result = volcano_subset(self.resource, query_params)
        self.assertTrue(len(result) == 2)

        # with 8 lines in the file (7 data rows), a 'frac'
        # of 0.3 will give 2 'other' rows
        query_params = {
            'pval': 0.03,
            'lfc': 0.5,
            'fraction': 0.3
        }
        result = volcano_subset(self.resource, query_params)
        self.assertTrue(len(result) == 4)
        j = json.dumps(result, indent=2)

        # with these parameters, we don't return any
        # results under that threshold. then, we only
        # return the 'other' 2 results
        query_params = {
            'pval': 0.001,
            'lfc': 0.5,
            'fraction': 0.3
        }
        result = volcano_subset(self.resource, query_params)
        self.assertTrue(len(result) == 2)

        # test that we watch errors:
        query_params = {
            'pval': -0.1, #<-- bad, negative
            'lfc': 0.5,
        }
        with self.assertRaisesRegex(Exception, 'positive float between'):
            volcano_subset(self.resource, query_params)

        query_params = {
            'pval': 0.1,
            'lfc': -0.5, #<-- bad, negative
        }
        with self.assertRaisesRegex(Exception, 'positive float'):
            volcano_subset(self.resource, query_params)

        query_params = {
            'pval': 0.1,
            'lfc': 0.5,
            'fraction': 1.5
        }
        with self.assertRaisesRegex(Exception, 'positive float between'):
            volcano_subset(self.resource, query_params)

        # check that it must be a particular resource type
        self.resource.resource_type = MATRIX_KEY
        self.resource.save()
        query_params = {
            'pval': 0.001,
            'lfc': 0.5,
            'fraction': 0.1
        }
        with self.assertRaisesRegex(Exception, 'Not an acceptable resource type'):
            volcano_subset(self.resource, query_params)

        # check using a file that doesn't have the correct column
        fp = os.path.join(self.TESTDIR, 'demo_file2.tsv')
        self.resource.resource_type = FEATURE_TABLE_KEY
        self.resource.file_format = TSV_FORMAT
        self.resource.save()
        associate_file_with_resource(self.resource, fp)
        query_params = {
            'pval': 0.03,
            'lfc': 0.5
        }
        with self.assertRaisesRegex(Exception, '"padj" and "log2FoldChange" column'):
            volcano_subset(self.resource, query_params)