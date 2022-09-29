import unittest
from copy import deepcopy

from data_structures.operation_input_spec import InputSpec
from data_structures.operation_output_spec import OutputSpec

from exceptions import AttributeValueError, \
    MissingAttributeKeywordError, \
    AttributeTypeError, \
    DataStructureValidationException


class TestInputOutputSpec(unittest.TestCase):

    def test_spec_without_default(self):
        spec = {
            'attribute_type': 'BoundedInteger',
            'min': 0,
            'max': 5
        }
        i = InputSpec(spec)
        dict_rep = i.to_dict()
        self.assertDictEqual(dict_rep, spec)
        o = OutputSpec(spec)
        dict_rep = o.to_dict()
        self.assertDictEqual(dict_rep, spec)

        spec = {
            'attribute_type': 'ObservationSet',
        }
        i = InputSpec(spec)
        dict_rep = i.to_dict()
        self.assertDictEqual(dict_rep, spec)
        o = OutputSpec(spec)
        dict_rep = o.to_dict()
        self.assertDictEqual(dict_rep, spec)

    def test_spec_with_default(self):
        spec = {
            'attribute_type': 'BoundedInteger',
            'min': 0,
            'max': 5,
            'default': 4
        }
        i = InputSpec(spec)
        dict_rep = i.to_dict()
        self.assertDictEqual(dict_rep, spec)
        o = OutputSpec(spec)
        dict_rep = o.to_dict()
        self.assertDictEqual(dict_rep, spec)

        spec = {
            'attribute_type': 'ObservationSet',
            'default': {
                'elements': []
            }
        }
        i = InputSpec(spec)
        dict_rep = i.to_dict()
        self.assertDictEqual(dict_rep, spec)
        o = OutputSpec(spec)
        dict_rep = o.to_dict()
        self.assertDictEqual(dict_rep, spec)

    def test_spec_with_invalid_default_fails(self):
        spec = {
            'attribute_type': 'BoundedInteger',
            'min': 0,
            'max': 5,
            'default': 100 # <-- out of bounds
        }
        with self.assertRaisesRegex(
            AttributeValueError, 'not within the bounds'):
            i = InputSpec(spec)

        with self.assertRaisesRegex(
            AttributeValueError, 'not within the bounds'):
            o = OutputSpec(spec)

        spec = {
            'attribute_type': 'ObservationSet',
            'default': [] # <-- should be a dict.
        }
        with self.assertRaisesRegex(DataStructureValidationException, 'expects a dict'):
            i = InputSpec(spec)
        with self.assertRaisesRegex(DataStructureValidationException, 'expects a dict'):
            i = OutputSpec(spec)

    def test_spec_with_invalid_format_fails(self):
        # this spec is missing the 'max' key:
        spec = {
            'attribute_type': 'BoundedInteger',
            'min': 0,
            'default': 3
        }
        with self.assertRaisesRegex(
            MissingAttributeKeywordError, "missing: 'max'"):
            i = InputSpec(spec)

        with self.assertRaisesRegex(
            MissingAttributeKeywordError, "missing: 'max'"):
            o = OutputSpec(spec)

    def test_with_invalid_attr_type(self):
        spec = {
            'attribute_type': 'GARBAGE',
            'default': 3
        }
        with self.assertRaisesRegex(AttributeTypeError, 'Could not locate type'):
            i = InputSpec(spec)

        with self.assertRaisesRegex(AttributeTypeError, 'Could not locate type'):
            i = OutputSpec(spec)

    def test_equality_overload(self):
        spec1 = {
            'attribute_type': 'BoundedInteger',
            'min': 0,
            'max': 5
        }
        spec2 = deepcopy(spec1)
        i1 = InputSpec(spec1)
        i2 = InputSpec(spec2)
        self.assertTrue(i1 == i2)

        # even adding a default to something that is otherwise the same
        # fails
        spec2['default'] = 3
        i2 = InputSpec(spec2)
        self.assertFalse(i1 == i2)

        spec2 = deepcopy(spec1)
        spec2['max'] = 3
        i2 = InputSpec(spec2)
        self.assertFalse(i1 == i2)