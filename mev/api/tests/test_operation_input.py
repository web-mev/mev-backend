import unittest

from rest_framework.exceptions import ValidationError

from api.data_structures.operation_input import OperationInput, BoundedIntegerInputSpec
from api.serializers.operation_input import OperationInputSerializer

class OperationInputTester(unittest.TestCase):


    def setUp(self):
        self.description = 'Some description'
        self.name = 'A name'
        self.min_val = 0
        self.max_val = 4
        self.default=2
        self.input_spec_dict = {
            'attribute_type': 'BoundedInteger', 
            'min': self.min_val, 
            'max': self.max_val, 
            'default':self.default
        }
        self.input_spec = BoundedIntegerInputSpec(
            min=self.min_val, 
            max=self.max_val, 
            default=self.default
        )
        self.expected_spec_result = {
            'attribute_type': 'BoundedInteger',
            'value': None, 
            'min': self.min_val, 
            'max': self.max_val, 
            'default':self.default
        }   
        self.valid_operation_input={
            'description': self.description, 
            'name': self.name, 
            'required': True, 
            'input_spec': self.input_spec_dict
        }


        self.expected_result = self.valid_operation_input.copy()
        self.expected_result['input_spec'] = self.expected_spec_result

    def test_serialization(self):
        '''
        Test that an OperationInput instance serializes to the expected
        dictionary representation
        '''
        o = OperationInput(self.description, self.name, self.input_spec, True)
        os = OperationInputSerializer(o)
        self.assertDictEqual(os.data, self.expected_result)

    def test_deserialization(self):
        '''
        Test that a JSON-like representation properly creates an OperationInput
        instance, or issues appropriate errors if malformatted.
        '''
        os = OperationInputSerializer(data=self.valid_operation_input)
        self.assertTrue(os.is_valid())
        self.assertDictEqual(os.data, self.expected_result)

        # missing `description`
        invalid_operation_input1={
            'name': self.name, 
            'required': True, 
            'input_spec': self.input_spec_dict
        }
        os = OperationInputSerializer(data=invalid_operation_input1)
        self.assertFalse(os.is_valid())

        # missing `name`
        invalid_operation_input2={
            'description': self.description, 
            'required': True, 
            'input_spec': self.input_spec_dict
        }
        os = OperationInputSerializer(data=invalid_operation_input2)
        self.assertFalse(os.is_valid())

        # missing `required`
        invalid_operation_input3={
            'description': self.description, 
            'name': self.name, 
            'input_spec': self.input_spec_dict
        }
        os = OperationInputSerializer(data=invalid_operation_input3)
        self.assertFalse(os.is_valid())

        # bad input_spec
        invalid_operation_input4={
            'description': self.description, 
            'name': self.name, 
            'required': True, 
            'input_spec': {'type':'foo'}
        }
        os = OperationInputSerializer(data=invalid_operation_input4)
        self.assertFalse(os.is_valid())