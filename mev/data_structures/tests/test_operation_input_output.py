import unittest
from copy import deepcopy

from data_structures.operation_input import OperationInput
from data_structures.operation_output import OperationOutput

from exceptions import AttributeValueError, \
    DataStructureValidationException


class TestOperationInputOutput(unittest.TestCase):
    '''
    Tests for the common behavior of OperationInput
    and OperationOutput.

    For common behavior, we often only bother to test the
    OperationInput
    '''
    def setUp(self):

        self.description = 'descriptive text.'
        self.name = 'Some name'
        self.converter = '...'
        self.spec = {
            "attribute_type": "PositiveInteger",
            "default": 3
        }
        self.input = {
            "description": self.description,
            "name": self.name,
            "required": True,
            "converter": self.converter,
            "spec": self.spec
        }
        self.output = {
            "required": True,
            "converter": self.converter,
            "spec": self.spec
        }

    def test_creation(self):
        '''
        Tests that we create an object and it has
        the correct serialized structure when we call
        to_dict
        '''
        o = OperationInput(self.input)
        dict_rep = o.to_dict()
        self.assertDictEqual(
            dict_rep,
            self.input
        )

        o = OperationOutput(self.output)
        dict_rep = o.to_dict()
        self.assertDictEqual(
            dict_rep,
            self.output
        )

    def test_missing_key_raises_ex(self):
        d = deepcopy(self.input)
        d.pop('description')
        d.pop('converter')
        with self.assertRaisesRegex(
            DataStructureValidationException, 
            '(description,converter)|(converter,description)'):
            o = OperationInput(d)

        d = deepcopy(self.output)
        d.pop('converter')
        with self.assertRaisesRegex(
            DataStructureValidationException, 
            'converter'):
            o = OperationOutput(d)

    def test_extra_input_key_raises_ex(self):
        d = deepcopy(self.input)
        d['extra'] = 'foo'
        with self.assertRaisesRegex(
            DataStructureValidationException, 
            'invalid extra keys: extra'):
            o = OperationInput(d)

        d = deepcopy(self.output)
        d['extra'] = 'foo'
        with self.assertRaisesRegex(
            DataStructureValidationException, 
            'invalid extra keys: extra'):
            o = OperationOutput(d)

    def test_required_key_options(self):
        '''
        Test that variations on True/False work
        in addition to the actual True/False booleans
        as json.load(s) might parse

        Since the logic is contained in the base class
        we only bother testing the OperationInput
        '''
        d = deepcopy(self.input)
        d['required'] = 0
        o = OperationInput(d)
        self.assertFalse(o.required)

        d['required'] = 1
        o = OperationInput(d)
        self.assertTrue(o.required)

        d['required'] = "1"
        o = OperationInput(d)
        self.assertTrue(o.required)

        d['required'] = "hi"
        with self.assertRaisesRegex(AttributeValueError, 'boolean'):
            o = OperationInput(d)

    def test_bad_spec_raises_ex(self):
        '''
        Test that exceptions with the nested objects
        are raised.
        '''
        d = deepcopy(self.input)
        bad_spec = {
            'attribute_type': 'BoundedFloat',
            'min': 0.0,
            'max': 1.0,
            'default': 2.1 #<-- BAD! 
        }
        d['spec'] = bad_spec
        with self.assertRaisesRegex(
            AttributeValueError, 
            'not within the bounds'):
            o = OperationInput(d)

    def test_equality_overload(self):

        i1 = OperationInput(self.input)
        i2 = OperationInput(self.input)
        self.assertTrue(i1 == i2)

        # specify 'required' key differently
        d = deepcopy(self.input)
        d['required'] = 1
        i2 = OperationInput(d)
        self.assertTrue(i1 == i2)

        d = deepcopy(self.input)
        d['name'] = d['name'] + '???'
        i2 = OperationInput(d)
        self.assertFalse(i1 == i2)

        d = deepcopy(self.output)
        o1 = OperationOutput(self.output)
        o2 = OperationOutput(d)
        self.assertTrue(o1 == o2)
