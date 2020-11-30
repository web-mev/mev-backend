import unittest
import uuid
import random

from rest_framework.serializers import ValidationError

from api.data_structures import IntegerInputSpec, \
    PositiveIntegerInputSpec, \
    NonnegativeIntegerInputSpec, \
    BoundedIntegerInputSpec, \
    FloatInputSpec, \
    PositiveFloatInputSpec, \
    NonnegativeFloatInputSpec, \
    BoundedFloatInputSpec, \
    StringInputSpec, \
    OptionStringInputSpec, \
    BooleanInputSpec, \
    DataResourceInputSpec, \
    ObservationInputSpec, \
    ObservationSetInputSpec, \
    FeatureInputSpec, \
    FeatureSetInputSpec, \
    OperationInput, \
    StringListInputSpec, \
    UnrestrictedStringListInputSpec
from api.serializers.input_spec import InputSpecSerializer

class TestInputSpec(unittest.TestCase):
    '''
    Tests the subclasses of the `InputSpec` class.
    These are classes that dictate the structure of `Operation`
    inputs and validate any default values. They don't take actual
    input values (as would be provided by a user)
    '''

    def test_integer_input_spec(self):
        i = IntegerInputSpec()
        i = IntegerInputSpec(default=3)
        self.assertTrue(i.default == 3)
        with self.assertRaises(ValidationError):
            i = IntegerInputSpec(default=3.5)
        with self.assertRaises(ValidationError):
            i = IntegerInputSpec(default=True)
        with self.assertRaises(ValidationError):
            i = IntegerInputSpec(default='abc')

    def test_nonnegativeinteger_input_spec(self):
        i = NonnegativeIntegerInputSpec()
        i = NonnegativeIntegerInputSpec(default=3)
        self.assertTrue(i.default == 3)
        i = NonnegativeIntegerInputSpec(default=0)
        self.assertTrue(i.default == 0)

        with self.assertRaises(ValidationError):
            i = NonnegativeIntegerInputSpec(default=-1)
        with self.assertRaises(ValidationError):
            i = NonnegativeIntegerInputSpec(default=3.5)
        with self.assertRaises(ValidationError):
            i = NonnegativeIntegerInputSpec(default=True)
        with self.assertRaises(ValidationError):
            i = NonnegativeIntegerInputSpec(default='abc')

    def test_positiveinteger_input_spec(self):
        i = PositiveIntegerInputSpec()
        i = PositiveIntegerInputSpec(default=3)
        self.assertTrue(i.default == 3)
        with self.assertRaises(ValidationError):
            i = PositiveIntegerInputSpec(default=0)
        with self.assertRaises(ValidationError):
            i = PositiveIntegerInputSpec(default=-1)
        with self.assertRaises(ValidationError):
            i = PositiveIntegerInputSpec(default=3.5)
        with self.assertRaises(ValidationError):
            i = PositiveIntegerInputSpec(default=True)
        with self.assertRaises(ValidationError):
            i = PositiveIntegerInputSpec(default='abc')

    def test_boundedinteger_input_spec(self):

        # need to specify min and max:
        with self.assertRaises(ValidationError):
            f = BoundedIntegerInputSpec()
        with self.assertRaises(ValidationError):
            f = BoundedIntegerInputSpec(default=2)

        # valid spec:
        f = BoundedIntegerInputSpec(min=0, max=2)
        f = BoundedIntegerInputSpec(min=0, max=2, default=1)
        self.assertTrue(f.default == 1)
        # max not an integer:
        with self.assertRaises(ValidationError):
            f = BoundedIntegerInputSpec(min=0, max=2.2) 
        # min not an integer:
        with self.assertRaises(ValidationError):
            f = BoundedIntegerInputSpec(min=0.2, max=2)

        # default not an integer:
        with self.assertRaises(ValidationError):
            f = BoundedIntegerInputSpec(min=0, max=2, default=1.1) 

        # default not in the range:
        with self.assertRaises(ValidationError):
            f = BoundedIntegerInputSpec(min=0, max=2, default=3) 
            
    def test_float_input_spec(self):
        i = FloatInputSpec()
        i = FloatInputSpec(default=3)
        i = FloatInputSpec(default=3.5)
        with self.assertRaises(ValidationError):
            i = FloatInputSpec(default=True)
        with self.assertRaises(ValidationError):
            i = FloatInputSpec(default='abc')

    def test_nonnegativefloat_input_spec(self):
        f = NonnegativeFloatInputSpec()
        f = NonnegativeFloatInputSpec(default=3)
        f = NonnegativeFloatInputSpec(default=0)
        f = NonnegativeFloatInputSpec(default=3.5)
        with self.assertRaises(ValidationError):
            f = NonnegativeFloatInputSpec(default=-1)
        with self.assertRaises(ValidationError):
            f = NonnegativeFloatInputSpec(default=True)
        with self.assertRaises(ValidationError):
            f = NonnegativeFloatInputSpec(default='abc')

    def test_positivefloat_input_spec(self):
        f = PositiveFloatInputSpec()
        f = PositiveFloatInputSpec(default=3)
        f = PositiveFloatInputSpec(default=3.5)

        with self.assertRaises(ValidationError):
            f = PositiveFloatInputSpec(default=0)
        with self.assertRaises(ValidationError):
            f = PositiveFloatInputSpec(default=-1)
        with self.assertRaises(ValidationError):
            f = PositiveFloatInputSpec(default=True)
        with self.assertRaises(ValidationError):
            f = PositiveFloatInputSpec(default='abc')

    def test_boundedfloat_input_spec(self):
        # need to specify min and max:
        with self.assertRaises(ValidationError):
            f = BoundedFloatInputSpec()
        with self.assertRaises(ValidationError):
            f = BoundedFloatInputSpec(default=2)

        # valid spec:
        f = BoundedFloatInputSpec(min=0, max=2)
        f = BoundedFloatInputSpec(min=0.1, max=2.2)
        f = BoundedFloatInputSpec(min=0.1, max=2)
        f = BoundedFloatInputSpec(min=0, max=2.2)
        f = BoundedFloatInputSpec(min=0, max=2, default=1.1) 

        # default not a Float:
        with self.assertRaises(ValidationError):
            f = BoundedFloatInputSpec(min=0, max=2, default='a') 

        # default not in the range:
        with self.assertRaises(ValidationError):
            f = BoundedFloatInputSpec(min=0, max=2, default=3.3) 

    def test_string_input_spec(self):
        s = StringInputSpec()
        s = StringInputSpec(default='abc')

        with self.assertRaises(ValidationError):
            s = StringInputSpec(default=1)
        with self.assertRaises(ValidationError):
            s = StringInputSpec(default=True)
        with self.assertRaises(ValidationError):
            s = StringInputSpec(default='')
        with self.assertRaises(ValidationError):
            s = StringInputSpec(default='--abc--')

    def test_optionstring_input_spec(self):
        s = OptionStringInputSpec(options=['abc', 'def'])
        s = OptionStringInputSpec(default='abc', options=['abc', 'def'])

        # missing "options" kwarg
        with self.assertRaises(ValidationError):
            s = OptionStringInputSpec(default='abc')

        # default is not among the valid options
        with self.assertRaises(ValidationError):
            s = OptionStringInputSpec(default='xyz', options=['abc', 'def'])

        # options is not a list (as required)
        with self.assertRaises(ValidationError):
            s = OptionStringInputSpec(options={})

        # options is a list, but not all items are strings
        with self.assertRaises(ValidationError):
            s = OptionStringInputSpec(default='abc', options=['abc', 10, 'def'])

    def test_boolean_input_spec(self):
        b = BooleanInputSpec()
        b = BooleanInputSpec(default=True)
        b = BooleanInputSpec(default='true')
        b = BooleanInputSpec(default=1)
        b = BooleanInputSpec(default=False)
        b = BooleanInputSpec(default='false')
        b = BooleanInputSpec(default=0)
        self.assertFalse(b.default)
        with self.assertRaises(ValidationError):
            b = BooleanInputSpec(default=33)
        with self.assertRaises(ValidationError):
            b = BooleanInputSpec(default=-1)
        with self.assertRaises(ValidationError):
            b = BooleanInputSpec(default='abc')

    def test_dataresource_input_spec(self):
        from resource_types import RESOURCE_MAPPING
        all_resource_types = list(RESOURCE_MAPPING.keys())
        random.shuffle(all_resource_types)
        n = 2
        valid_resource_types = [all_resource_types[i] for i in range(n)]

        ds = DataResourceInputSpec(many=True, resource_types=valid_resource_types)
        ds = DataResourceInputSpec(many=1, resource_types=valid_resource_types)
        ds = DataResourceInputSpec(many='true', resource_types=valid_resource_types)
        
        # missing `resource_types` key
        with self.assertRaises(ValidationError):
            ds = DataResourceInputSpec(many=True)
        # missing `many` key
        with self.assertRaises(ValidationError):
            ds = DataResourceInputSpec(resource_types=valid_resource_types)

        # `many` key cannot be cast as a boolean
        with self.assertRaises(ValidationError):
            ds = DataResourceInputSpec(many='yes', resource_types=valid_resource_types)

        # `resource_types` key has bad values
        with self.assertRaises(ValidationError):
            ds = DataResourceInputSpec(many=True, resource_types=['abc',])

        # `resource_types` key is not a list
        with self.assertRaises(ValidationError):
            ds = DataResourceInputSpec(many=True, resource_types=valid_resource_types[0])

    def test_stringlist_input_spec(self):
        s = StringListInputSpec()
        x = StringListInputSpec(default=['abc', 'def'])

        with self.assertRaises(ValidationError):
            s = StringListInputSpec(default=['abc', '???'])
            
        with self.assertRaises(ValidationError):
            s = StringListInputSpec(default='abc')

        with self.assertRaises(ValidationError):
            s = StringListInputSpec(xyz='def')
        with self.assertRaises(ValidationError):
            s = StringListInputSpec(default='???')

    def test_unrestrictedstringlist_input_spec(self):
        s = UnrestrictedStringListInputSpec()
        x = UnrestrictedStringListInputSpec(default=['abc', '???'])

        with self.assertRaises(ValidationError):
            s = UnrestrictedStringListInputSpec(default='abc')
        with self.assertRaises(ValidationError):
            s = UnrestrictedStringListInputSpec(default='???')
        with self.assertRaises(ValidationError):
            s = UnrestrictedStringListInputSpec(xyz='def')

class InputSpecSerializerTester(unittest.TestCase):

    def setUp(self):

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
            'min': self.min_val, 
            'max': self.max_val, 
            'default':self.default
        }

    def test_list_types_serialization(self):
        spec = StringListInputSpec(default=['abc', 'xyz'])
        i = InputSpecSerializer(spec)
        self.assertDictEqual(i.data, {'attribute_type': 'StringList', 'default': ['abc', 'xyz']})
        
        spec = StringListInputSpec(default=['a b'])
        i = InputSpecSerializer(spec)
        # below, note that the default didn't change to "a_b". The value of "a b" (with a space)
        # is valid, and that's all that gets checked.
        self.assertDictEqual(i.data, {'attribute_type': 'StringList', 'default': ['a b']})
       
        spec = UnrestrictedStringListInputSpec(default=['a?b', 'xyz'])
        i = InputSpecSerializer(spec)
        self.assertDictEqual(i.data, {'attribute_type': 'UnrestrictedStringList', 'default': ['a?b', 'xyz']})

    def test_serialization(self):
        '''
        Test that an InputSpec instance serializes to the expected
        dictionary representation
        '''
        i = InputSpecSerializer(self.input_spec)
        self.assertDictEqual(i.data, self.expected_spec_result)

    def test_deserialization(self):
        '''
        Test that a JSON-like representation properly creates an OperationInput
        instance, or issues appropriate errors if malformatted.
        '''
        i = InputSpecSerializer(data=self.input_spec_dict)
        self.assertTrue(i.is_valid())
        self.assertDictEqual(i.data, self.expected_spec_result)

        # missing default is ok.
        input_spec_dict = {
            'attribute_type': 'BoundedInteger', 
            'min': self.min_val, 
            'max': self.max_val
        }
        i = InputSpecSerializer(data=input_spec_dict)
        self.assertTrue(i.is_valid())

        # the attribute_type is not valid
        invalid_input_spec_dict = {
            'attribute_type': 'Some bad type', 
            'min': self.min_val, 
            'max': self.max_val, 
            'default':self.default
        }
        i = InputSpecSerializer(data=invalid_input_spec_dict)
        self.assertFalse(i.is_valid())

        # default is not within the bounds
        invalid_input_spec_dict = {
            'attribute_type': 'BoundedInteger', 
            'min': self.min_val, 
            'max': self.max_val, 
            'default':self.max_val + 1
        }
        i = InputSpecSerializer(data=invalid_input_spec_dict)
        self.assertFalse(i.is_valid())

        # missing 'min' key
        invalid_input_spec_dict = {
            'attribute_type': 'BoundedInteger', 
            'max': self.max_val, 
            'default':self.default
        }
        i = InputSpecSerializer(data=invalid_input_spec_dict)
        self.assertFalse(i.is_valid())

    def test_non_native_types(self):
        '''
        The other tests use the children of the Attribute classes to 
        produce their serialized/deserialized representation.

        Here, we test the "other" input spec types, such as those for
        Observations, ObservationSets, etc.
        '''
        types_to_test = {'Observation':ObservationInputSpec, 
            'ObservationSet':ObservationSetInputSpec,
            'Feature': FeatureInputSpec,
            'FeatureSet': FeatureSetInputSpec
        }
        for t,tt in types_to_test.items():
            spec_dict = {
                'attribute_type': t
            }
            x = InputSpecSerializer(data=spec_dict)
            self.assertTrue(x.is_valid())
            i = tt()
            x = InputSpecSerializer(i)
            self.assertEqual(x.data, spec_dict)
