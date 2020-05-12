import unittest

from rest_framework.exceptions import ValidationError

from api.data_structures import Observation, \
    IntegerAttribute, \
    FloatAttribute, \
    StringAttribute, \
    BoundedFloatAttribute, \
    BoundedIntegerAttribute
from api.serializers import ObservationSerializer
from api.exceptions import StringIdentifierException


class TestObservationSerializer(unittest.TestCase):

    def setUp(self):
        float_attr = FloatAttribute(0.01)
        int_attr = IntegerAttribute(3)
        bounded_float_attr = BoundedFloatAttribute(0.1, min=0.0, max=1.0)

        self.demo_observation = Observation(
            'my_identifier', 
            {'keyA': float_attr, 'keyB':int_attr}
        )

        self.demo_observation2 = Observation('my_identifier', {})

        self.demo_observation_data = {
            'id': 'my_identifier', 
            'attributes':{
                'keyA':{'attribute_type':'Float', 'value': 0.01},
                'keyB':{'attribute_type':'Integer', 'value': 3}
            }
        }

        self.demo_observation_data2 = {
            'id': 'my_identifier', 
            'attributes':{}
        }

        self.bad_observation_data = {
            'id': 'my_identifier', 
            'attributes':{
                'keyA':{'attribute_type':'Float', 'value': 'abc'},
                'keyB':{'attribute_type':'Integer', 'value': 3}
            }
        }

        self.demo_observation_data_w_bounds = {
            'id': 'my_identifier', 
            'attributes':{
                'pvalue':{
                    'attribute_type':'BoundedFloat', 
                    'value': 0.1, 
                    'min':0.0, 
                    'max':1.0
                },
                'keyB':{'attribute_type':'Integer', 'value': 3}
            }
        }
        self.demo_observation_w_bounds = Observation(
            'my_identifier', 
            {'pvalue': bounded_float_attr, 'keyB':int_attr}
        )


        self.bad_demo_observation_data_w_bounds = {
            'id': 'my_identifier', 
            'attributes':{
                'pvalue':{
                    'attribute_type':'BoundedFloat', 
                    'value': 1.1, # out of bounds!!
                    'min':0.0, 
                    'max':1.0
                },
                'keyB':{'attribute_type':'Integer', 'value': 3}
            }
        }


    def test_expected_deserialization(self):
        '''
        Tests a full-featured Observation
        '''
        obs_s = ObservationSerializer(data=self.demo_observation_data)
        self.assertTrue(obs_s.is_valid())
        obs = obs_s.get_instance()

        # note that equality of Observations is only determined by the 
        # name/identifier.  We will check all the attributes here also.
        self.assertEqual(obs, self.demo_observation)
        for attr_name, attr in obs.attributes.items():
            expected_attr = self.demo_observation.attributes[attr_name]
            self.assertEqual(expected_attr, attr)

    def test_expected_deserialization_case2(self):
        '''
        Tests deserialization with missing attribute dict,
        which is valid since Observations are not required
        to have one.
        '''
        data = {'id': 'my_identifier'}
        obs_s = ObservationSerializer(data=data)
        self.assertTrue(obs_s.is_valid())
        obs = obs_s.get_instance()
        self.assertEqual({}, obs.attributes)

    def test_expected_deserialization_case3(self):
        '''
        Tests deserialization with empty attribute dict
        '''
        data = {'id': 'my_identifier', 'attributes':{}}
        obs_s = ObservationSerializer(data=data)
        self.assertTrue(obs_s.is_valid())
        obs = obs_s.get_instance()
        self.assertEqual({}, obs.attributes)

    def test_expected_deserialization_case4(self):
        '''
        Tests when attributes is a non-dict
        '''
        # here an empty list is given for attributes
        data = {'id': 'my_identifier', 'attributes':[]}
        obs_s = ObservationSerializer(data=data)
        self.assertFalse(obs_s.is_valid())

        # here, a string given for attributes
        data = {'id': 'my_identifier', 'attributes':'abc'}
        obs_s = ObservationSerializer(data=data)
        self.assertFalse(obs_s.is_valid())

    def test_expected_deserialization_case5(self):
        '''
        Tests when bad attributes are passed
        '''
        obs_s = ObservationSerializer(data=self.bad_observation_data)
        self.assertFalse(obs_s.is_valid())

    def test_expected_deserialization_case6(self):
        '''
        Tests when the identifier "name" is invalid
        '''
        data = {'id': 'my-bad-id-', 'attributes':{}}
        obs_s = ObservationSerializer(data=data)
        self.assertFalse(obs_s.is_valid())

    def test_expected_deserialization_case7(self):
        '''
        Tests a full-featured Observation where one of the attributes
        is a bounded float
        '''
        obs_s = ObservationSerializer(data=self.demo_observation_data_w_bounds)
        self.assertTrue(obs_s.is_valid())

        obs = obs_s.get_instance()

        # note that equality of Observations is only determined by the 
        # name/identifier.  We will check all the attributes here also.
        self.assertEqual(obs, self.demo_observation_w_bounds)
        for attr_name, attr in obs.attributes.items():
            expected_attr = self.demo_observation_w_bounds.attributes[attr_name]
            self.assertEqual(expected_attr, attr)

    def test_expected_deserialization_case8(self):
        '''
        Tests a full-featured Observation where one of the attributes
        is a bounded float, BUT it is out-of-bounds
        '''
        obs_s = ObservationSerializer(data=self.bad_demo_observation_data_w_bounds)
        self.assertFalse(obs_s.is_valid())

    def test_attribute_with_missing_value_is_invalid(self):
        '''
        The attribute is missing its value.
        Other tests check validity of attributes at a 'lower level'
        and this is just a secondary check.
        '''
        data = {'id': 'my_identifier', 
            'attributes':{
                'keyA':{'attribute_type':'Float'}
            }
        }
        obs_s = ObservationSerializer(data=data)
        self.assertFalse(obs_s.is_valid())

    def test_serialization(self):
        '''
        Check that Observation instances are correctly
        serialized into json-like structures.
        '''
        s = ObservationSerializer(self.demo_observation)
        self.assertDictEqual(s.data, self.demo_observation_data)
        s = ObservationSerializer(self.demo_observation2)
        self.assertDictEqual(s.data, self.demo_observation_data2)
        s = ObservationSerializer(self.demo_observation_w_bounds)
        self.assertDictEqual(s.data, self.demo_observation_data_w_bounds)


class TestObservation(unittest.TestCase):

    def setUp(self):
        float_attr = FloatAttribute(0.01)
        int_attr = IntegerAttribute(3)
        self.demo_observation = Observation(
            'my_identifier', 
            {'keyA': float_attr, 'keyB':int_attr}
        )

    def test_bad_identifier_raises_exception(self):
        '''
        Test that names with incompatible
        characters are rejected
        '''

        # cannot have strange characters:
        with self.assertRaises(StringIdentifierException):
            o = Observation('a#b')

        # cannot start with a number
        with self.assertRaises(StringIdentifierException):
            o = Observation('9a')

        # Can't start or end with the dash or dot.
        # The question mark is just a "generic" out-of-bound character
        chars = ['-', '.', '?'] 
        for c in chars:
            # cannot start with this char
            test_name = c + 'abc'
            with self.assertRaises(StringIdentifierException):
                o = Observation(test_name)

            # cannot end with this char
            test_name = 'abc' + c
            with self.assertRaises(StringIdentifierException):
                o = Observation(test_name)

    def test_name_with_space_normalized(self):
        o = Observation('A name')
        self.assertEqual(o.id, 'A_name')

    def test_adding_duplicate_attribute_raises_error(self):
        '''
        Test that trying to add an attribute fails when the key
        already existed (i.e. they cannot overwrite an existing
        attribute.)
        '''
        with self.assertRaises(ValidationError):
            self.demo_observation.add_attribute(
                'keyA', 
                {'attribute_type': 'Float', 'value': 2.3}
            )
        
    def test_adding_ovewrite_attribute(self):
        '''
        Test overwriting an existing attribute
        '''
        float_attr = FloatAttribute(0.01)
        int_attr = IntegerAttribute(3)
        observation = Observation(
            'some_identifier', 
            {'keyA': float_attr, 'keyB':int_attr}
        )
        observation.add_attribute(
            'keyA', 
            {'attribute_type': 'Float', 'value': 2.3},
            overwrite=True
        )
        expected_attr = FloatAttribute(2.3)
        self.assertEqual(
            observation.attributes['keyA'],
            expected_attr)

    def test_adding_new_attribute(self):
        '''
        Test adding a new attribute
        '''
        float_attr = FloatAttribute(0.01)
        int_attr = IntegerAttribute(3)
        observation = Observation(
            'some_identifier', 
            {'keyA': float_attr, 'keyB':int_attr}
        )
        observation.add_attribute(
            'keyC', 
            {'attribute_type': 'String', 'value': 'abc'}
        )
        expected_attr = StringAttribute('abc')
        self.assertEqual(
            observation.attributes['keyC'],
            expected_attr)

        expected_keys = set(['keyA', 'keyB', 'keyC'])
        existing_keys = set(observation.attributes.keys())
        self.assertTrue(expected_keys == existing_keys)

    def test_adding_bad_attribute_raises_error(self):
        '''
        Here the attribute has a type in conflict with its
        value.  They key is new, so it COULD be added
        if the value was valid.
        '''
        with self.assertRaises(ValidationError):
            self.demo_observation.add_attribute(
                'keyC', 
                {'attribute_type': 'Integer', 'value': 2.3}
            )