import unittest
from copy import deepcopy

from data_structures.operation_input import OperationInput
from data_structures.operation_output import OperationOutput

from exceptions import AttributeValueError, \
    DataStructureValidationException, \
    NullAttributeError


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

    def test_extra_keys_are_permitted_with_kwarg(self):
        '''
        We DO permit extra keyword args (which are ignored)
        if we pass the correct keyword to the `check_value`
        method.

        This is particularly relevant for 'complex' types
        like Observation/FeatureSets. For ex, our frontend
        application may carry additional data (like color,
        name, etc.) that are useful for the frontend, but
        not used on the backend. This makes it a little 
        easier on the frontend.
        '''
        spec = {
            "attribute_type": "ObservationSet"
        }
        input = {
            "description": "",
            "name": "",
            "required": True,
            "converter": "",
            "spec": spec
        }
        o = OperationInput(input)
        good_value = {
            'elements': [
                {
                    'id': 'sampleA'
                }
            ]
        }
        o.check_value(good_value)

        good_value_with_extra = {
            'color': 'red',
            'elements': [
                {
                    'id': 'sampleA'
                }
            ]
        }
        # if we don't pass the explicit kwarg, then we raise an ex:
        with self.assertRaisesRegex(DataStructureValidationException, 'color'):
            o.check_value(good_value_with_extra)
        with self.assertRaisesRegex(DataStructureValidationException, 'color'):
            o.check_value(good_value_with_extra, ignore_extra_keys=False)
        # if the ignore_extra_keys kwarg is passed, we allow 
        # extra keys (and ignore them). Also check that it doesn't
        # modify the actual data structure:
        o.check_value(good_value_with_extra, ignore_extra_keys=True)
        self.assertDictEqual(o.to_dict(), input)

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

    def test_data_resource_input_method(self):
        '''
        For convenience, we provide a method that checks
        whether an input/output corresponds to one of our
        file-inputs (DataResource, etc.)

        Here we check that it works as expected
        '''
        dr_spec = {
            "attribute_type": "DataResource",
            "many": False,
            "resource_type": "MTX"
        }
        variable_dr_spec = {
            "attribute_type": "VariableDataResource",
            "many": False,
            "resource_types": ["MTX", "ANN"]
        }
        dr_input = {
            "description": 'some desc',
            "name": 'a name',
            "required": True,
            "converter": '',
            "spec": dr_spec
        }
        variable_dr_input = {
            "description": 'some desc',
            "name": 'a name',
            "required": True,
            "converter": '',
            "spec": variable_dr_spec
        }
        i = OperationInput(dr_input)
        self.assertTrue(i.is_data_resource_input())
        i = OperationInput(variable_dr_input)
        self.assertTrue(i.is_data_resource_input())

        # this one corresponds to a PositiveInteger:
        i = OperationInput(self.input)
        self.assertFalse(i.is_data_resource_input())

    def test_check_value_method(self):

        # this one corresponds to a PositiveInteger:
        i = OperationInput(self.input)
        i.check_value(4)
        with self.assertRaisesRegex(AttributeValueError, 'not a positive integer'):
            i.check_value(-4)

        # try with an optional input
        input_dict = {
            "description": 'some desc',
            "name": 'a name',
            "required": False,
            "converter": '',
            "spec": {
                "attribute_type": "PositiveInteger",
                "default": 3
            }
        }
        i = OperationInput(input_dict)
        i.check_value(None)

        input_dict['required'] = True
        i = OperationInput(input_dict)
        with self.assertRaises(NullAttributeError):
            i.check_value(None)