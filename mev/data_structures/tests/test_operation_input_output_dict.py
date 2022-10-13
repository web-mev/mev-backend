import unittest
from copy import deepcopy

from data_structures.operation_input_output_dict import OperationInputDict, \
    OperationOutputDict
from data_structures.operation_input import OperationInput

from exceptions import AttributeValueError, \
    DataStructureValidationException


class TestOperationInputOutputDict(unittest.TestCase):
    def setUp(self):

        self.input1 = {
            "description": 'descriptive text.',
            "name": 'some name',
            "required": True,
            "converter": 'some.converter',
            "spec": {
                "attribute_type": "PositiveInteger",
                "default": 3
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
                "attribute_type": "PositiveInteger",
                "default": 5
            }
        }

        self.input_dict = {
            'keyA': self.input1,
            'keyB': self.input2
        }
        self.output_dict = {
            'keyC': self.output
        }

    def test_basic_creation_works(self):
        i = OperationInputDict(self.input_dict)
        dict_rep = i.to_dict()
        self.assertDictEqual(
            dict_rep,
            self.input_dict
        )

        o = OperationOutputDict(self.output_dict)
        dict_rep = o.to_dict()
        self.assertDictEqual(
            dict_rep,
            self.output_dict
        )

    def test_indexer_works(self):
        '''
        Test that the dict-like accessor works
        as expected
        '''
        i = OperationInputDict(self.input_dict)
        x0 = i['keyA']
        x1 = OperationInput(self.input1)
        self.assertTrue(x0 == x1)

    def test_bad_input_fails(self):
        with self.assertRaisesRegex(
            DataStructureValidationException, 'expects a dict'):
            i = OperationInputDict(['a'])

    def test_equality_overload(self):
        '''
        Test that the equality operater works
        '''
        i1 = OperationInputDict(self.input_dict)
        i2 = OperationInputDict(self.input_dict)
        self.assertTrue(i1 == i2)

        # same keys in the dict, but the nested
        # OperationInput is slightly different
        input1_copy = deepcopy(self.input1)
        # change the description field:
        input1_copy['description'] = 'something'
        modified_input_dict = {
            'keyA': input1_copy,
            'keyB': self.input2
        }
        i2 = OperationInputDict(modified_input_dict)
        self.assertFalse(i1 == i2)

        # different keys. Obviously should fail.
        i1 = OperationInputDict(self.input_dict)
        modified_input_dict = self.input_dict.copy()
        modified_input_dict.pop('keyA')
        i2 = OperationInputDict(modified_input_dict)
        self.assertFalse(i1 == i2)    

    def test_fails_bad_input(self):
        input1 = {
            "description": 'descriptive text.',
            "name": 'some name',
            "required": True,
            "converter": 'some.converter',
            "spec": {
                "attribute_type": "PositiveInteger",
                "default": -3 # <--- BAD
            }
        }
        with self.assertRaisesRegex(
            AttributeValueError, 'not a positive integer'):
            i = OperationInputDict({'some_input': input1})

        input1 = {
            "description": 'descriptive text.',
            # missing 'name' key
            "required": True,
            "converter": 'some.converter',
            "spec": {
                "attribute_type": "PositiveInteger",
                "default": 3
            }
        }
        with self.assertRaisesRegex(
            DataStructureValidationException, 'name'):
            i = OperationInputDict({'some_input': input1})