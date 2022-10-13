import unittest
import uuid
from copy import deepcopy

from data_structures.operation import Operation

from exceptions import DataStructureValidationException, \
    AttributeValueError, \
    MissingAttributeKeywordError


class TestOperation(unittest.TestCase):

    def setUp(self):

        self.input1 = {
            "description": 'descriptive text.',
            "name": 'some name',
            "required": True,
            "converter": 'some.converter',
            "spec": {
                "attribute_type": "BoundedFloat",
                "min": 0,
                "max": 1.0,
                "default": 0.05
            }
        }
        self.input2 = {
            "description": 'descriptive text.',
            "name": 'other name',
            "required": True,
            "converter": 'some.converter',
            "spec": {
                "attribute_type": "DataResource",
                "resource_type": "XYZ",
                "many": False
            }
        }
        self.output = {
            "required": True,
            "converter": 'someconverter',
            "spec": {
                "attribute_type": "DataResource",
                "resource_type": "XYZ",
                "many": False
            }
        }

        self.input_dict = {
            'inputA': self.input1,
            'inputB': self.input2
        }
        self.output_dict = {
            'outputA': self.output
        }

        self.operation_dict = {
            'id': str(uuid.uuid4()),
            'description': 'description',
            'name': 'the op name',
            'mode': 'local_docker',
            'repository_url': 'https://github.com/abc.git',
            'repository_name': 'abc',
            'git_hash': 'abc123',
            'workspace_operation': True,
            'inputs': self.input_dict,
            'outputs': self.output_dict
        }

    def test_creation(self):
        op = Operation(self.operation_dict)
        dict_rep = op.to_dict()
        expected_dict = self.operation_dict
        self.assertDictEqual(dict_rep, expected_dict)

    def test_bad_id(self):
        op_dict = deepcopy(self.operation_dict)
        op_dict['id'] = 'foo'
        with self.assertRaisesRegex(AttributeValueError, 'not a valid UUID'):
            Operation(op_dict)

    def test_equality_overload(self):
        
        op1 = Operation(self.operation_dict)
        d2 = deepcopy(self.operation_dict)
        op2 = Operation(d2)
        self.assertTrue(op1 == op2)

        # change one of the inputs
        d2['inputs'].pop('inputB')
        op2 = Operation(d2)
        self.assertFalse(op1 == op2)
