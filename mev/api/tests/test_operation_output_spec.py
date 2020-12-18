import unittest
import uuid
import random

from rest_framework.serializers import ValidationError

from api.data_structures import IntegerOutputSpec, \
    PositiveIntegerOutputSpec, \
    NonnegativeIntegerOutputSpec, \
    BoundedIntegerOutputSpec, \
    FloatOutputSpec, \
    PositiveFloatOutputSpec, \
    NonnegativeFloatOutputSpec, \
    BoundedFloatOutputSpec, \
    StringOutputSpec, \
    OptionStringOutputSpec, \
    BooleanOutputSpec, \
    DataResourceOutputSpec, \
    ObservationOutputSpec, \
    ObservationSetOutputSpec, \
    FeatureOutputSpec, \
    FeatureSetOutputSpec, \
    OperationOutput, \
    StringListOutputSpec, \
    UnrestrictedStringListOutputSpec
from api.serializers.output_spec import OutputSpecSerializer

class TestOutputSpec(unittest.TestCase):
    '''
    Tests the subclasses of the `OutputSpec` class.
    These are classes that dictate the structure of `Operation`
    outputs and validate any default values. They don't take actual
    output values (as would be provided by an analysis)
    '''

    def test_integer_output_spec(self):
        i = IntegerOutputSpec()
        i = IntegerOutputSpec(default=3)
        self.assertTrue(i.default == 3)
        with self.assertRaises(ValidationError):
            i = IntegerOutputSpec(default=3.5)
        with self.assertRaises(ValidationError):
            i = IntegerOutputSpec(default=True)
        with self.assertRaises(ValidationError):
            i = IntegerOutputSpec(default='abc')

    def test_nonnegativeinteger_output_spec(self):
        i = NonnegativeIntegerOutputSpec()
        i = NonnegativeIntegerOutputSpec(default=3)
        self.assertTrue(i.default == 3)
        i = NonnegativeIntegerOutputSpec(default=0)
        self.assertTrue(i.default == 0)

        with self.assertRaises(ValidationError):
            i = NonnegativeIntegerOutputSpec(default=-1)
        with self.assertRaises(ValidationError):
            i = NonnegativeIntegerOutputSpec(default=3.5)
        with self.assertRaises(ValidationError):
            i = NonnegativeIntegerOutputSpec(default=True)
        with self.assertRaises(ValidationError):
            i = NonnegativeIntegerOutputSpec(default='abc')

    def test_positiveinteger_output_spec(self):
        i = PositiveIntegerOutputSpec()
        i = PositiveIntegerOutputSpec(default=3)
        self.assertTrue(i.default == 3)
        with self.assertRaises(ValidationError):
            i = PositiveIntegerOutputSpec(default=0)
        with self.assertRaises(ValidationError):
            i = PositiveIntegerOutputSpec(default=-1)
        with self.assertRaises(ValidationError):
            i = PositiveIntegerOutputSpec(default=3.5)
        with self.assertRaises(ValidationError):
            i = PositiveIntegerOutputSpec(default=True)
        with self.assertRaises(ValidationError):
            i = PositiveIntegerOutputSpec(default='abc')

    def test_boundedinteger_output_spec(self):

        # need to specify min and max:
        with self.assertRaises(ValidationError):
            f = BoundedIntegerOutputSpec()
        with self.assertRaises(ValidationError):
            f = BoundedIntegerOutputSpec(default=2)

        # valid spec:
        f = BoundedIntegerOutputSpec(min=0, max=2)
        self.assertEqual(f.min_value, 0)
        self.assertEqual(f.max_value, 2)
        f = BoundedIntegerOutputSpec(min=0, max=2, default=1)
        self.assertTrue(f.default == 1)
        # max not an integer:
        with self.assertRaises(ValidationError):
            f = BoundedIntegerOutputSpec(min=0, max=2.2) 
        # min not an integer:
        with self.assertRaises(ValidationError):
            f = BoundedIntegerOutputSpec(min=0.2, max=2)

        # default not an integer:
        with self.assertRaises(ValidationError):
            f = BoundedIntegerOutputSpec(min=0, max=2, default=1.1) 

        # default not in the range:
        with self.assertRaises(ValidationError):
            f = BoundedIntegerOutputSpec(min=0, max=2, default=3) 
            
    def test_float_output_spec(self):
        i = FloatOutputSpec()
        i = FloatOutputSpec(default=3)
        i = FloatOutputSpec(default=3.5)
        with self.assertRaises(ValidationError):
            i = FloatOutputSpec(default=True)
        with self.assertRaises(ValidationError):
            i = FloatOutputSpec(default='abc')

    def test_nonnegativefloat_output_spec(self):
        f = NonnegativeFloatOutputSpec()
        f = NonnegativeFloatOutputSpec(default=3)
        f = NonnegativeFloatOutputSpec(default=0)
        f = NonnegativeFloatOutputSpec(default=3.5)
        with self.assertRaises(ValidationError):
            f = NonnegativeFloatOutputSpec(default=-1)
        with self.assertRaises(ValidationError):
            f = NonnegativeFloatOutputSpec(default=True)
        with self.assertRaises(ValidationError):
            f = NonnegativeFloatOutputSpec(default='abc')

    def test_positivefloat_output_spec(self):
        f = PositiveFloatOutputSpec()
        f = PositiveFloatOutputSpec(default=3)
        f = PositiveFloatOutputSpec(default=3.5)

        with self.assertRaises(ValidationError):
            f = PositiveFloatOutputSpec(default=0)
        with self.assertRaises(ValidationError):
            f = PositiveFloatOutputSpec(default=-1)
        with self.assertRaises(ValidationError):
            f = PositiveFloatOutputSpec(default=True)
        with self.assertRaises(ValidationError):
            f = PositiveFloatOutputSpec(default='abc')

    def test_boundedfloat_output_spec(self):
        # need to specify min and max:
        with self.assertRaises(ValidationError):
            f = BoundedFloatOutputSpec()
        with self.assertRaises(ValidationError):
            f = BoundedFloatOutputSpec(default=2)

        # valid spec:
        f = BoundedFloatOutputSpec(min=0, max=2)
        self.assertEqual(f.min_value, 0)
        self.assertEqual(f.max_value, 2)
        f = BoundedFloatOutputSpec(min=0.1, max=2.2)
        f = BoundedFloatOutputSpec(min=0.1, max=2)
        f = BoundedFloatOutputSpec(min=0, max=2.2)
        f = BoundedFloatOutputSpec(min=0, max=2, default=1.1) 

        # default not a Float:
        with self.assertRaises(ValidationError):
            f = BoundedFloatOutputSpec(min=0, max=2, default='a') 

        # default not in the range:
        with self.assertRaises(ValidationError):
            f = BoundedFloatOutputSpec(min=0, max=2, default=3.3) 

    def test_string_output_spec(self):
        s = StringOutputSpec()
        s = StringOutputSpec(default='abc')

        with self.assertRaises(ValidationError):
            s = StringOutputSpec(default=1)
        with self.assertRaises(ValidationError):
            s = StringOutputSpec(default=True)
        with self.assertRaises(ValidationError):
            s = StringOutputSpec(default='')
        with self.assertRaises(ValidationError):
            s = StringOutputSpec(default='--abc--')

    def test_optionstring_output_spec(self):
        s = OptionStringOutputSpec(options=['abc', 'def'])
        s = OptionStringOutputSpec(default='abc', options=['abc', 'def'])

        # missing "options" kwarg
        with self.assertRaises(ValidationError):
            s = OptionStringOutputSpec(default='abc')

        # default is not among the valid options
        with self.assertRaises(ValidationError):
            s = OptionStringOutputSpec(default='xyz', options=['abc', 'def'])

        # options is not a list (as required)
        with self.assertRaises(ValidationError):
            s = OptionStringOutputSpec(options={})

        # options is a list, but not all items are strings
        with self.assertRaises(ValidationError):
            s = OptionStringOutputSpec(default='abc', options=['abc', 10, 'def'])

    def test_boolean_output_spec(self):
        b = BooleanOutputSpec()
        b = BooleanOutputSpec(default=True)
        b = BooleanOutputSpec(default='true')
        b = BooleanOutputSpec(default=1)
        b = BooleanOutputSpec(default=False)
        b = BooleanOutputSpec(default='false')
        b = BooleanOutputSpec(default=0)
        self.assertFalse(b.default)
        with self.assertRaises(ValidationError):
            b = BooleanOutputSpec(default=33)
        with self.assertRaises(ValidationError):
            b = BooleanOutputSpec(default=-1)
        with self.assertRaises(ValidationError):
            b = BooleanOutputSpec(default='abc')

    def test_dataresource_output_spec(self):
        from resource_types import RESOURCE_MAPPING
        all_resource_type = list(RESOURCE_MAPPING.keys())
        random.shuffle(all_resource_type)
        valid_resource_type = all_resource_type[0]

        ds = DataResourceOutputSpec(many=True, resource_type=valid_resource_type)
        ds = DataResourceOutputSpec(many=1, resource_type=valid_resource_type)
        ds = DataResourceOutputSpec(many='true', resource_type=valid_resource_type)
        
        # missing `resource_type` key
        with self.assertRaises(ValidationError):
            ds = DataResourceOutputSpec(many=True)

        # missing `many` key
        with self.assertRaises(ValidationError):
            ds = DataResourceOutputSpec(resource_type=valid_resource_type)

        # `many` key cannot be cast as a boolean
        with self.assertRaises(ValidationError):
            ds = DataResourceOutputSpec(many='yes', resource_type=valid_resource_type)

        # `resource_type` key has bad value
        with self.assertRaises(ValidationError):
            ds = DataResourceOutputSpec(many=True, resource_type='abc')

        # `resource_type` key is a list
        with self.assertRaises(ValidationError):
            ds = DataResourceOutputSpec(many=True, resource_type=[valid_resource_type,])

        # `resource_type` key is a wildcard (e.g. for remote uploads where we don't 
        # know ahead of time what the file type is)
        ds = DataResourceOutputSpec(many=True, resource_type='*')

    def test_stringlist_output_spec(self):
        s = StringListOutputSpec()

        s = StringListOutputSpec(default=['abc', 'def'])

        with self.assertRaises(ValidationError):
            s = StringListOutputSpec(default=['abc', '???'])

        with self.assertRaises(ValidationError):
            s = StringListOutputSpec(default='abc')

        with self.assertRaises(ValidationError):
            s = StringListOutputSpec(xyz='def')
        with self.assertRaises(ValidationError):
            s = StringListOutputSpec(default=['???'])

    def test_unrestrictedstringlist_output_spec(self):
        s = UnrestrictedStringListOutputSpec()

        s = UnrestrictedStringListOutputSpec(default=['abc', '???'])

        with self.assertRaises(ValidationError):
            s = UnrestrictedStringListOutputSpec(default='abc')
        with self.assertRaises(ValidationError):
            s = UnrestrictedStringListOutputSpec(default='???')

        with self.assertRaises(ValidationError):
            s = UnrestrictedStringListOutputSpec(xyz=['def', 'abc'])

class OutputSpecSerializerTester(unittest.TestCase):

    def setUp(self):

        self.min_val = 0
        self.max_val = 4
        self.default=2
        self.output_spec_dict = {
            'attribute_type': 'BoundedInteger', 
            'min': self.min_val, 
            'max': self.max_val, 
            'default':self.default
        }
        self.output_spec = BoundedIntegerOutputSpec(
            min=self.min_val, 
            max=self.max_val, 
            default=self.default
        )
        self.expected_spec_result = {
            'attribute_type': 'BoundedInteger',
            'min': self.min_val, 
            'max': self.max_val, 
            'default':self.default
        } 

    def test_list_types_serialization(self):
        spec = StringListOutputSpec(default=['abc', 'xyz'])
        i = OutputSpecSerializer(spec)
        self.assertDictEqual(i.data, {'attribute_type': 'StringList', 'default': ['abc', 'xyz']})
        
        spec = StringListOutputSpec(default=['a b'])
        i = OutputSpecSerializer(spec)
        # below, note that the default didn't change to "a_b". The value of "a b" (with a space)
        # is valid, and that's all that gets checked.
        self.assertDictEqual(i.data, {'attribute_type': 'StringList', 'default': ['a b']})
       
        spec = UnrestrictedStringListOutputSpec(default=['a?b', 'xyz'])
        i = OutputSpecSerializer(spec)
        self.assertDictEqual(i.data, {'attribute_type': 'UnrestrictedStringList', 
            'default': ['a?b', 'xyz']})


    def test_serialization(self):
        '''
        Test that an OutputSpec instance serializes to the expected
        dictionary representation
        '''
        i = OutputSpecSerializer(self.output_spec)
        self.assertDictEqual(i.data, self.expected_spec_result)

    def test_deserialization(self):
        '''
        Test that a JSON-like representation properly creates an OperationOutput
        instance, or issues appropriate errors if malformatted.
        '''
        i = OutputSpecSerializer(data=self.output_spec_dict)
        self.assertTrue(i.is_valid())
        ii = i.get_instance()
        self.assertDictEqual(ii.to_dict(), self.expected_spec_result)

        # missing default is ok.
        output_spec_dict = {
            'attribute_type': 'BoundedInteger', 
            'min': self.min_val, 
            'max': self.max_val
        }
        i = OutputSpecSerializer(data=output_spec_dict)
        self.assertTrue(i.is_valid())

        # the attribute_type is not valid
        invalid_output_spec_dict = {
            'attribute_type': 'Some bad type', 
            'min': self.min_val, 
            'max': self.max_val, 
            'default':self.default
        }
        i = OutputSpecSerializer(data=invalid_output_spec_dict)
        self.assertFalse(i.is_valid())

        # default is not within the bounds
        invalid_output_spec_dict = {
            'attribute_type': 'BoundedInteger', 
            'min': self.min_val, 
            'max': self.max_val, 
            'default':self.max_val + 1
        }
        i = OutputSpecSerializer(data=invalid_output_spec_dict)
        self.assertFalse(i.is_valid())

        # missing 'min' key
        invalid_output_spec_dict = {
            'attribute_type': 'BoundedInteger', 
            'max': self.max_val, 
            'default':self.default
        }
        i = OutputSpecSerializer(data=invalid_output_spec_dict)
        self.assertFalse(i.is_valid())

        # test that the wildcard output type without 'many' key is rejected
        ds_spec_dict = {
            'attribute_type': 'DataResource', 
            'resource_type': '*'
        }
        i = OutputSpecSerializer(data=ds_spec_dict)
        self.assertFalse(i.is_valid())

        # test that the wildcard output type is fine
        ds_spec_dict = {
            'attribute_type': 'DataResource', 
            'resource_type': '*',
            'many': True
        }
        i = OutputSpecSerializer(data=ds_spec_dict)
        self.assertTrue(i.is_valid())

    def test_non_native_types(self):
        '''
        The other tests use the children of the Attribute classes to 
        produce their serialized/deserialized representation.

        Here, we test the "other" input spec types, such as those for
        Observations, ObservationSets, etc.
        '''
        types_to_test = {'Observation':ObservationOutputSpec, 
            'ObservationSet':ObservationSetOutputSpec,
            'Feature': FeatureOutputSpec,
            'FeatureSet': FeatureSetOutputSpec
        }
        for t,tt in types_to_test.items():
            spec_dict = {
                'attribute_type': t
            }
            x = OutputSpecSerializer(data=spec_dict)
            self.assertTrue(x.is_valid())
            i = tt()
            x = OutputSpecSerializer(i)
            self.assertEqual(x.data, spec_dict)