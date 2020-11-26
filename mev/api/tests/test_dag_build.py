import unittest
import unittest.mock as mock
import uuid
import datetime

from django.core.exceptions import ImproperlyConfigured

from api.models import WorkspaceExecutedOperation, Operation, Workspace
from api.data_structures import DagNode, SimpleDag
from api.utilities.operations import create_workspace_dag
from api.tests.base import BaseAPITestCase

class DagBuildTester(BaseAPITestCase):

    def setUp(self):
        '''
        Tests that we create the expected graph given a mocked set of 
        Operations and resources
        '''

        self.establish_clients()

        # create the mock data to be returned:
        # Doesn'thave to be a fully-compliant dict- just needs the inputs/outputs

        # for the first op, we have 2 input files and 3 output files.
        # There are also a couple other inputs/outputs that are NOT files,
        # so they are not shown in the graph
        self.op1_data = {
            'name': 'foo',
            'inputs': {
                'op1input1': {
                    'description': 'Some input', 
                    'name': 'fileA:', 
                    'required': True, 
                    'spec': {
                        'attribute_type': 'DataResource', 
                        'resource_types': ['I_MTX', 'EXP_MTX'], 
                        'many': False
                    }
                }, 
                'op1input2': {
                    'description': 'Some other input', 
                    'name': 'fileB:', 
                    'required': True, 
                    'spec': {
                        'attribute_type': 'DataResource', 
                        'resource_types': ['ANN'], 
                        'many': False
                    }
                }, 
                'p_val': {
                    'description': 'The filtering threshold for the p-value', 
                    'name': 'P-value threshold:', 
                    'required': False, 
                    'spec': {
                        'attribute_type': 'BoundedFloat', 
                        'min': 0, 
                        'max': 1.0, 
                        'default': 0.05
                    }
                }
            },
            'outputs':{
                'op1output1': {
                    'spec': {
                        'attribute_type': 'DataResource', 
                        'resource_type': 'EXP_MTX', 
                        'many': False
                    }
                }, 
                'op1output2': {
                    'spec': {
                        'attribute_type': 'DataResource', 
                        'resource_type': 'EXP_MTX', 
                        'many': False
                    }
                },
                'op1output3': {
                    'spec': {
                        'attribute_type': 'DataResource', 
                        'resource_type': 'EXP_MTX', 
                        'many': False
                    }
                },
                'fdr': {
                    'spec': {
                        'attribute_type': 'Integer'
                    }
                }
            }
        }
        self.op2_data = {
            'name': 'bar',
            'inputs': {
                'op2input1': {
                    'description': 'Some input', 
                    'name': 'aaa:', 
                    'required': True, 
                    'spec': {
                        'attribute_type': 'DataResource', 
                        'resource_types': ['I_MTX'], 
                        'many': False
                    }
                }, 
                'op2input2': {
                    'description': 'Some other input', 
                    'name': 'bbb:', 
                    'required': True, 
                    'spec': {
                        'attribute_type': 'DataResource', 
                        'resource_types': ['ANN'], 
                        'many': False
                    }
                }, 
                'xyz': {
                    'description': 'The filtering threshold for the p-value', 
                    'name': 'P-value threshold:', 
                    'required': False, 
                    'spec': {
                        'attribute_type': 'BoundedFloat', 
                        'min': 0, 
                        'max': 1.0, 
                        'default': 0.05
                    }
                }
            },
            'outputs':{
                'op2output1': {
                    'spec': {
                        'attribute_type': 'DataResource', 
                        'resource_type': 'EXP_MTX', 
                        'many': False
                    }
                }
            }
        }
        mock_inputs1 = {
            'op1input1': 'A',
            'op1input2': 'B',
            'p_val': 0.1
        }
        mock_inputs2 = {
            'op2input1': 'C',
            'op2input2': 'D',
            'xyz': 0.1
        }
        mock_outputs1 = {
            'op1output1': 'C',
            'op1output2': 'D',
            'op1output3': 'E',
            'fdr': 0.05
        }
        mock_outputs2 = {
            'op2output1': 'F'
        }

        # create two executed ops. Assign to them the same Operation,
        # since the Operation doesn't matter-- we mock out the function
        # which reads the specs.

        ops = Operation.objects.all()
        if len(ops) == 0:
            raise ImproperlyConfigured('Need at least one Operation in the database.')
        op = ops[0]
        workspaces = Workspace.objects.all()
        if len(workspaces) == 0:
            raise ImproperlyConfigured('Need at least one Workspace in the database.')
        workspace = workspaces[0]

        u1 = uuid.uuid4()
        u2 = uuid.uuid4()
        self.ex1 = WorkspaceExecutedOperation.objects.create(
            id=u1,
            owner = self.regular_user_1,
            workspace=workspace,
            job_name = 'jobA',
            inputs = mock_inputs1,
            outputs = mock_outputs1,
            operation = op,
            mode = 'xyz',
            status = WorkspaceExecutedOperation.SUBMITTED
        )
        self.ex2 = WorkspaceExecutedOperation.objects.create(
            id=u2,
            owner = self.regular_user_1,
            workspace=workspace,
            job_name = 'jobB',
            inputs = mock_inputs2,
            outputs = mock_outputs2,
            operation = op,
            mode = 'abc',
            status = WorkspaceExecutedOperation.SUBMITTED
        )
        self.expected_parents = {
            str(self.ex1.pk): ['A', 'B'],
            'A': [],
            'B': [],
            'C': [str(self.ex1.pk)],
            'D': [str(self.ex1.pk)],
            'E': [str(self.ex1.pk)],
            str(self.ex2.pk): ['C', 'D'],
            'F': [str(self.ex2.pk)]
        }

    @mock.patch('api.utilities.operations.get_operation_instance_data')
    @mock.patch('api.utilities.operations.get_resource_by_pk')
    def test_graph_builder(self, mock_get_resource_by_pk, mock_get_operation_instance_data):
        '''
        Here we mock that we have two operations completed and check that the 
        graph structure is as expected
        '''        
        mock_get_operation_instance_data.side_effect = [self.op1_data, self.op2_data]
        mock_resource = mock.MagicMock()
        mock_resource.name = 'abc'
        mock_get_resource_by_pk.return_value = mock_resource
        # add stop datetimes to both ops so we see the full tree
        self.ex1.execution_stop_datetime = datetime.datetime.now()
        self.ex2.execution_stop_datetime = datetime.datetime.now()
        dag = create_workspace_dag([self.ex1, self.ex2])
        nodes_present = []
        for node in dag:
            node_id = node['id']
            nodes_present.append(node_id)
            parents = node['parentIds']
            self.assertCountEqual(parents, self.expected_parents[node_id])
        self.assertCountEqual(nodes_present, ['A','B', 'C', 'D', 'E', 'F', str(self.ex1.pk),str(self.ex2.pk)])

    @mock.patch('api.utilities.operations.get_operation_instance_data')
    @mock.patch('api.utilities.operations.get_resource_by_pk')
    def test_graph_builder_with_unfinished_op(self, mock_get_resource_by_pk, mock_get_operation_instance_data):
        '''
        Here we mock that we have only op1 completed and check that the 
        graph structure is as expected. Namely, want to ensure that the output
        of the second op is NOT there (node F)
        '''        
        mock_get_operation_instance_data.side_effect = [self.op1_data, self.op2_data]
        mock_resource = mock.MagicMock()
        mock_resource.name = 'abc'
        mock_get_resource_by_pk.return_value = mock_resource
        # add stop datetimes to both ops so we see the full tree
        self.ex1.execution_stop_datetime = datetime.datetime.now()
        dag = create_workspace_dag([self.ex1, self.ex2])
        nodes_present = []
        for node in dag:
            node_id = node['id']
            nodes_present.append(node_id)
            parents = node['parentIds']
            self.assertCountEqual(parents, self.expected_parents[node_id])
        self.assertCountEqual(nodes_present, ['A','B', 'C', 'D', 'E', str(self.ex1.pk),str(self.ex2.pk)])
        self.assertFalse('F' in nodes_present) # explicitly double-check that 'F' is NOT there

    @mock.patch('api.utilities.operations.get_operation_instance_data')
    @mock.patch('api.utilities.operations.get_resource_by_pk')
    def test_graph_builder_with_failed_op(self, mock_get_resource_by_pk, mock_get_operation_instance_data):
        '''
        Here we mock that we have only op1 completed and check that the 
        graph structure is as expected. We pretend the second operation failed,
        so we should NOT see that 
        '''        
        mock_get_operation_instance_data.side_effect = [self.op1_data, self.op2_data]
        mock_resource = mock.MagicMock()
        mock_resource.name = 'abc'
        mock_get_resource_by_pk.return_value = mock_resource
        # add stop datetimes to both ops so we see the full tree
        self.ex1.execution_stop_datetime = datetime.datetime.now()
        self.ex2.execution_stop_datetime = datetime.datetime.now()
        self.ex2.job_failed = True
        dag = create_workspace_dag([self.ex1, self.ex2])
        nodes_present = []
        for node in dag:
            node_id = node['id']
            nodes_present.append(node_id)
            parents = node['parentIds']
            self.assertCountEqual(parents, self.expected_parents[node_id])
        self.assertCountEqual(nodes_present, ['A','B', 'C', 'D', 'E', str(self.ex1.pk)])
        self.assertFalse('F' in nodes_present) # explicitly double-check that 'F' is NOT there
        # explicitly double-check that the second op is NOT there        
        self.assertFalse(str(self.ex2.pk) in nodes_present)