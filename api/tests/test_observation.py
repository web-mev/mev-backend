import unittest

from rest_framework.exceptions import ValidationError

from api.data_structures import Observation, \
    IntegerAttribute, \
    FloatAttribute, \
    StringAttribute
from api.serializers import ObservationSerializer
from api.exceptions import StringIdentifierException


class TestObservationSerializer(unittest.TestCase):

    def setUp(self):
        float_attr = FloatAttribute(0.01)
        int_attr = IntegerAttribute(3)
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
        Tests deserialization with missing attribute dict
        '''
        data = {'id': 'my_identifier'}
        obs_s = ObservationSerializer(data=data)
        self.assertTrue(obs_s.is_valid())
        obs = obs_s.get_instance()

    def test_expected_deserialization_case3(self):
        '''
        Tests deserialization with empty attribute dict
        '''
        data = {'id': 'my_identifier', 'attributes':{}}
        obs_s = ObservationSerializer(data=data)
        self.assertTrue(obs_s.is_valid())
        obs = obs_s.get_instance()

    def test_expected_deserialization_case4(self):
        '''
        Tests when attributes is a non-dict
        '''
        data = {'id': 'my_identifier', 'attributes':[]}
        obs_s = ObservationSerializer(data=data)
        self.assertFalse(obs_s.is_valid())

        data = {'id': 'my_identifier', 'attributes':'abc'}
        obs_s = ObservationSerializer(data=data)
        self.assertFalse(obs_s.is_valid())

    def test_expected_deserialization_case5(self):
        '''
        Tests when bad attributes are passed
        '''
        obs_s = ObservationSerializer(data=self.bad_observation_data)
        self.assertFalse(obs_s.is_valid())

    def test_attribute_with_missing_value_raises_ex(self):
        data = {'id': 'my_identifier', 
            'attributes':{
                'keyA':{'attribute_type':'Float'}
            }
        }
        obs_s = ObservationSerializer(data=data)
        self.assertFalse(obs_s.is_valid())

    def test_serialization(self):
        s = ObservationSerializer(self.demo_observation)
        self.assertDictEqual(s.data, self.demo_observation_data)
        s = ObservationSerializer(self.demo_observation2)
        self.assertDictEqual(s.data, self.demo_observation_data2)


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
        value.  They key is new
        '''
        with self.assertRaises(ValidationError):
            self.demo_observation.add_attribute(
                'keyC', 
                {'attribute_type': 'Integer', 'value': 2.3}
            )