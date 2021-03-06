import unittest
import random

from rest_framework.exceptions import ValidationError

from resource_types import RESOURCE_MAPPING
from api.data_structures.operation_output import OperationOutput
from api.data_structures.operation_output_spec import BoundedIntegerOutputSpec, \
    DataResourceOutputSpec
from api.serializers.operation_output import OperationOutputSerializer

class OperationOutputTester(unittest.TestCase):

    def setUp(self):
        self.min_val = 0
        self.max_val = 4
        self.output_spec_dict1 = {
            'attribute_type': 'BoundedInteger', 
            'min': self.min_val, 
            'max': self.max_val, 
        }
        self.output_spec1 = BoundedIntegerOutputSpec(
            min=self.min_val, 
            max=self.max_val
        )
        self.expected_spec_result1 = {
            'attribute_type': 'BoundedInteger',
            'min': self.min_val, 
            'max': self.max_val 
        }   
        self.valid_operation_output1={ 
            'spec': self.output_spec_dict1
        }
        self.expected_result1 = self.valid_operation_output1.copy()
        self.expected_result1['spec'] = self.expected_spec_result1

        all_resource_types = list(RESOURCE_MAPPING.keys())
        random.shuffle(all_resource_types)
        self.rt = all_resource_types[0] 
        self.output_spec_dict2 = {
            'attribute_type': 'DataResource', 
            'resource_type': self.rt,
            'many': False
        }
        self.output_spec2 = DataResourceOutputSpec(
            many=False, 
            resource_type=self.rt
        )
        self.expected_spec_result2 = {
            'attribute_type': 'DataResource',
            'many': False, 
            'resource_type': self.rt
        }   
        self.valid_operation_output2={ 
            'spec': self.output_spec_dict2
        }
        self.expected_result2 = self.valid_operation_output2.copy()
        self.expected_result2['spec'] = self.expected_spec_result2

    def test_serialization(self):
        '''
        Test that an OperationOutput instance serializes to the expected
        dictionary representation
        '''
        o = OperationOutput(self.output_spec1)
        os = OperationOutputSerializer(o)
        self.assertDictEqual(os.data, self.expected_result1)

        o = OperationOutput(self.output_spec2)
        os = OperationOutputSerializer(o)
        self.assertDictEqual(os.data, self.expected_result2)

    def test_deserialization(self):
        '''
        Test that a JSON-like representation properly creates an OperationOutput
        instance, or issues appropriate errors if malformatted.
        '''
        os = OperationOutputSerializer(data=self.valid_operation_output1)
        os.is_valid(raise_exception=True)
        
        self.assertTrue(os.is_valid())
        self.assertDictEqual(os.data, self.expected_result1)

        os = OperationOutputSerializer(data=self.valid_operation_output2)
        self.assertTrue(os.is_valid())
        self.assertDictEqual(os.data, self.expected_result2)

        # give it a bad input_spec to see that the error percolates:
        invalid_operation_output1={
            'spec': {
                'attribute_type': 'DataResource', 
                'resource_type': 'foo',
                'many': False
            }
        }
        os = OperationOutputSerializer(data=invalid_operation_output1)
        self.assertFalse(os.is_valid())