import unittest
import uuid
import random
import copy
import json
import os

from api.runners import AVAILABLE_RUNNERS
from resource_types import RESOURCE_MAPPING
from api.serializers.operation import OperationSerializer
from api.data_structures.operation import Operation
from api.data_structures import OperationInputDict, OperationOutputDict
from api.serializers.operation_input import OperationInputSerializer
from api.serializers.operation_output import OperationOutputSerializer
from api.serializers.operation_input_dict import OperationInputDictSerializer
from api.serializers.operation_output_dict import OperationOutputDictSerializer

TESTDIR = os.path.dirname(__file__)
TESTDIR = os.path.join(TESTDIR, 'operation_test_files')

class OperationTester(unittest.TestCase):
    def setUp(self):

        all_resource_types = list(RESOURCE_MAPPING.keys())
        random.shuffle(all_resource_types)

        # an OperationInput
        self.op_input1_dict = {
            'description': 'The count matrix of expressions',
            'name': 'Count matrix:',
            'required': True,
            'converter': 'api.converters.data_resource.LocalDockerSingleDataResourceConverter',
            'spec': {
                'attribute_type': 'DataResource',
                'resource_type': all_resource_types[0],
                'many': False
            }
        }
        # another OperationInput
        self.op_input2_dict={
            'description': 'The filtering threshold for the p-value',
            'name': 'P-value threshold:',
            'required': False,
            'converter': 'api.converters.basic_attributes.BoundedFloatAttributeConverter',
            'spec': {
                'attribute_type': 'BoundedFloat',
                'min': 0,
                'max': 1.0,
                'default': 0.05
            }
        }
        self.op_output1_dict = {
            'required': True,
            'converter': 'tmp',
            'spec': {
                'attribute_type': 'DataResource',
                'resource_type': all_resource_types[0],
                'many': False
            }
        }
        self.op_output2_dict = {
            'required': True,
            'converter': 'tmp',
            'spec': {
                'attribute_type': 'DataResource',
                'resource_type': all_resource_types[1],
                'many': True
            }
        }

        op_input1 = OperationInputSerializer(data=self.op_input1_dict).get_instance()
        op_input2 = OperationInputSerializer(data=self.op_input2_dict).get_instance()
        op_output1 = OperationOutputSerializer(data=self.op_output1_dict).get_instance()
        op_output2 = OperationOutputSerializer(data=self.op_output2_dict).get_instance()

        self.op_id = str(uuid.uuid4())
        self.op_name = 'Some name'
        self.description = 'Here is some desc.'
        self.mode = AVAILABLE_RUNNERS[0]
        self.repository_url = 'https://github.com/some-repo/'
        self.git_hash = 'abcd1234'
        self.repo_name = 'some-repo'
        self.workspace_operation = True
        inputs_dict = {
            'count_matrix': self.op_input1_dict,
            'p_val': self.op_input2_dict
        }
        outputs_dict =  {
            'norm_counts': self.op_output1_dict,
            'dge_table': self.op_output2_dict
        }
        self.operation_dict = {
            'id': self.op_id,
            'name': self.op_name,
            'description': self.description,
            'inputs': inputs_dict,
            'outputs': outputs_dict,
            'mode': self.mode, 
            'repository_url': self.repository_url,
            'git_hash': self.git_hash,
            'repo_name': self.repo_name,
            'workspace_operation': self.workspace_operation
        }
        op_input_dict = OperationInputDictSerializer(data=inputs_dict).get_instance()
        op_output_dict = OperationOutputDictSerializer(data=outputs_dict).get_instance()
        self.operation_instance = Operation(
            self.op_id,
            self.op_name,
            self.description,
            op_input_dict,
            op_output_dict,
            self.mode,
            self.repository_url,
            self.git_hash,
            self.repo_name,
            self.workspace_operation
        )

    def test_serialization(self):
        o = OperationSerializer(self.operation_instance)
        expected_data = self.operation_dict.copy()
        self.assertDictEqual(expected_data,o.data)


    def test_deserialization(self):
        o = OperationSerializer(data=self.operation_dict)
        self.assertTrue(o.is_valid(raise_exception=True))
        new_instance = o.get_instance()
        self.assertEqual(new_instance.inputs, self.operation_instance.inputs)

        # bad identifier (not a UUID):
        bad_dict = copy.deepcopy(self.operation_dict)
        bad_dict['id'] = 'abc'
        o = OperationSerializer(data=bad_dict)
        self.assertFalse(o.is_valid()) 

        # mess up one of the inputs:
        bad_dict = copy.deepcopy(self.operation_dict)
        o = OperationSerializer(data=bad_dict) # just check that it starts out OK
        self.assertTrue(o.is_valid()) 
        max_val = bad_dict['inputs']['p_val']['spec']['max']
        bad_dict['inputs']['p_val']['spec']['default'] = max_val + 0.1
        o = OperationSerializer(data=bad_dict)
        self.assertFalse(o.is_valid()) 

        # change the mode to something invalid, check that it fails validation:
        bad_mode = 'foo'
        bad_dict = copy.deepcopy(self.operation_dict)
        o = OperationSerializer(data=bad_dict) # just check that it starts out OK
        self.assertTrue(o.is_valid(raise_exception=True)) 
        bad_dict['mode'] = bad_mode
        o = OperationSerializer(data=bad_dict)
        self.assertFalse(o.is_valid())  

        # check that the repo field can be blank, etc.
        # For operations that are not pulled from github, etc.
        # we want to allow those fields to be blank.
        valid_dict = copy.deepcopy(self.operation_dict)
        valid_dict['git_hash'] = ''
        valid_dict['repo_name'] = ''
        valid_dict['repository_url'] = ''
        o = OperationSerializer(data=valid_dict)
        self.assertTrue(o.is_valid())  