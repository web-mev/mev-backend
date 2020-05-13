import unittest

from rest_framework.exceptions import ValidationError

from api.data_structures import Observation, \
    Feature, \
    IntegerAttribute, \
    FloatAttribute, \
    StringAttribute, \
    BoundedFloatAttribute, \
    BoundedIntegerAttribute
from api.serializers import ObservationSerializer, FeatureSerializer
from api.exceptions import StringIdentifierException


class ElementSerializerTester(object):
    '''
    This class allows us to test children of `BaseElement`, 
    such as `Observation`s or `Feature`s with a consistent
    set of tests.  If specialization is required, those
    cases can be handled in the actual TestCase class
    '''
    def __init__(self, element_serializer_class):

        # "registers" the specific Serializer we are testing
        # (e.g. ObservationSerializer)
        self.element_serializer_class = element_serializer_class


    def test_expected_deserialization(self, testcase):
        '''
        Tests a full-featured Element
        '''
        element_serializer = self.element_serializer_class(data=testcase.demo_element_data)
        testcase.assertTrue(element_serializer.is_valid())
        element = element_serializer.get_instance()

        # note that equality of Elements is only determined by the 
        # name/identifier.  We will check all the attributes here also.
        testcase.assertEqual(element, testcase.demo_element)
        for attr_name, attr in element.attributes.items():
            expected_attr = testcase.demo_element.attributes[attr_name]
            testcase.assertEqual(expected_attr, attr)

    def test_expected_deserialization_case2(self, testcase):
        '''
        Tests deserialization with missing attribute dict,
        which is valid since Observations are not required
        to have one.
        '''
        data = {'id': 'my_identifier'}
        element_serializer = self.element_serializer_class(data=data)
        testcase.assertTrue(element_serializer.is_valid())
        element = element_serializer.get_instance()
        testcase.assertEqual({}, element.attributes)

    def test_expected_deserialization_case3(self, testcase):
        '''
        Tests deserialization with empty attribute dict
        '''
        data = {'id': 'my_identifier', 'attributes':{}}
        element_serializer = self.element_serializer_class(data=data)
        testcase.assertTrue(element_serializer.is_valid())
        element = element_serializer.get_instance()
        testcase.assertEqual({}, element.attributes)

    def test_expected_deserialization_case4(self, testcase):
        '''
        Tests when attributes is a non-dict
        '''
        # here an empty list is given for attributes
        data = {'id': 'my_identifier', 'attributes':[]}
        element_serializer = self.element_serializer_class(data=data)
        testcase.assertFalse(element_serializer.is_valid())

        # here, a string given for attributes
        data = {'id': 'my_identifier', 'attributes':'abc'}
        element_serializer = self.element_serializer_class(data=data)
        testcase.assertFalse(element_serializer.is_valid())

    def test_expected_deserialization_case5(self, testcase):
        '''
        Tests when bad attributes are passed
        '''
        element_serializer = self.element_serializer_class(data=testcase.bad_element_data)
        testcase.assertFalse(element_serializer.is_valid())

    def test_expected_deserialization_case6(self, testcase):
        '''
        Tests when the identifier "name" is invalid
        '''
        data = {'id': 'my-bad-id-', 'attributes':{}}
        element_serializer = self.element_serializer_class(data=data)
        testcase.assertFalse(element_serializer.is_valid())

    def test_expected_deserialization_case7(self, testcase):
        '''
        Tests a full-featured Observation where one of the attributes
        is a bounded float
        '''
        element_serializer = self.element_serializer_class(data=testcase.demo_element_data_w_bounds)
        testcase.assertTrue(element_serializer.is_valid())

        element = element_serializer.get_instance()

        # note that equality of Observations is only determined by the 
        # name/identifier.  We will check all the attributes here also.
        testcase.assertEqual(element, testcase.demo_element_w_bounds)
        for attr_name, attr in element.attributes.items():
            expected_attr = testcase.demo_element_w_bounds.attributes[attr_name]
            testcase.assertEqual(expected_attr, attr)

    def test_expected_deserialization_case8(self, testcase):
        '''
        Tests a full-featured Observation where one of the attributes
        is a bounded float, BUT it is out-of-bounds
        '''
        element_serializer = self.element_serializer_class(data=testcase.bad_demo_element_data_w_bounds)
        testcase.assertFalse(element_serializer.is_valid())

    def test_attribute_with_missing_value_is_invalid(self, testcase):
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
        element_serializer = self.element_serializer_class(data=data)
        testcase.assertFalse(element_serializer.is_valid())

    def test_serialization(self, testcase):
        '''
        Check that Observation instances are correctly
        serialized into json-like structures.
        '''
        s = self.element_serializer_class(testcase.demo_element)
        testcase.assertDictEqual(s.data, testcase.demo_element_data)
        s = self.element_serializer_class(testcase.demo_element2)
        testcase.assertDictEqual(s.data, testcase.demo_element_data2)
        s = self.element_serializer_class(testcase.demo_element_w_bounds)
        testcase.assertDictEqual(s.data, testcase.demo_element_data_w_bounds)




class TestObservationSerializer(unittest.TestCase):

    def setUp(self):
        float_attr = FloatAttribute(0.01)
        int_attr = IntegerAttribute(3)
        bounded_float_attr = BoundedFloatAttribute(0.1, min=0.0, max=1.0)

        self.demo_element = Observation(
            'my_identifier', 
            {'keyA': float_attr, 'keyB':int_attr}
        )

        self.demo_element2 = Observation('my_identifier', {})

        self.demo_element_data = {
            'id': 'my_identifier', 
            'attributes':{
                'keyA':{'attribute_type':'Float', 'value': 0.01},
                'keyB':{'attribute_type':'Integer', 'value': 3}
            }
        }

        self.demo_element_data2 = {
            'id': 'my_identifier', 
            'attributes':{}
        }

        self.bad_element_data = {
            'id': 'my_identifier', 
            'attributes':{
                'keyA':{'attribute_type':'Float', 'value': 'abc'},
                'keyB':{'attribute_type':'Integer', 'value': 3}
            }
        }

        self.demo_element_data_w_bounds = {
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
        self.demo_element_w_bounds = Observation(
            'my_identifier', 
            {'pvalue': bounded_float_attr, 'keyB':int_attr}
        )


        self.bad_demo_element_data_w_bounds = {
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

        # the class that will execute the tests
        self.tester_class = ElementSerializerTester(ObservationSerializer)

    def test_observation_serializer(self):
        test_methods = [x for x in dir(self.tester_class) if x.startswith('test_')]
        for t in test_methods:
            m = getattr(self.tester_class, t)
            m(self)


class TestFeatureSerializer(unittest.TestCase):

    def setUp(self):
        float_attr = FloatAttribute(0.01)
        int_attr = IntegerAttribute(3)
        bounded_float_attr = BoundedFloatAttribute(0.1, min=0.0, max=1.0)

        self.demo_element = Feature(
            'my_identifier', 
            {'keyA': float_attr, 'keyB':int_attr}
        )

        self.demo_element2 = Feature('my_identifier', {})

        self.demo_element_data = {
            'id': 'my_identifier', 
            'attributes':{
                'keyA':{'attribute_type':'Float', 'value': 0.01},
                'keyB':{'attribute_type':'Integer', 'value': 3}
            }
        }

        self.demo_element_data2 = {
            'id': 'my_identifier', 
            'attributes':{}
        }

        self.bad_element_data = {
            'id': 'my_identifier', 
            'attributes':{
                'keyA':{'attribute_type':'Float', 'value': 'abc'},
                'keyB':{'attribute_type':'Integer', 'value': 3}
            }
        }

        self.demo_element_data_w_bounds = {
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
        self.demo_element_w_bounds = Feature(
            'my_identifier', 
            {'pvalue': bounded_float_attr, 'keyB':int_attr}
        )


        self.bad_demo_element_data_w_bounds = {
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

        # the class that will execute the tests
        self.tester_class = ElementSerializerTester(FeatureSerializer)

    def test_observation_serializer(self):
        test_methods = [x for x in dir(self.tester_class) if x.startswith('test_')]
        for t in test_methods:
            m = getattr(self.tester_class, t)
            m(self)


class ElementTester(object):
    '''
    This allows us to have a set of common testing functions for 
    children of the `Element` class.  Any tests specific to the children
    (e.g. an `Observation`) can be handled in a specific TestCase instance.
    '''
    def __init__(self, element_class):
        self.element_class = element_class

    def test_bad_identifier_raises_exception(self, testcase):
        '''
        Test that names with incompatible
        characters are rejected
        '''

        # cannot have strange characters:
        with testcase.assertRaises(StringIdentifierException):
            o = self.element_class('a#b')

        # cannot start with a number
        with testcase.assertRaises(StringIdentifierException):
            o = self.element_class('9a')

        # Can't start or end with the dash or dot.
        # The question mark is just a "generic" out-of-bound character
        chars = ['-', '.', '?'] 
        for c in chars:
            # cannot start with this char
            test_name = c + 'abc'
            with testcase.assertRaises(StringIdentifierException):
                o = self.element_class(test_name)

            # cannot end with this char
            test_name = 'abc' + c
            with testcase.assertRaises(StringIdentifierException):
                o = self.element_class(test_name)

    def test_name_with_space_normalized(self, testcase):
        o = self.element_class('A name')
        testcase.assertEqual(o.id, 'A_name')

    def test_adding_duplicate_attribute_raises_error(self, testcase):
        '''
        Test that trying to add an attribute fails when the key
        already existed (i.e. they cannot overwrite an existing
        attribute unless `overwrite=True` is passed as an argument.)
        '''
        with testcase.assertRaises(ValidationError):
            testcase.demo_element.add_attribute(
                'keyA', 
                {'attribute_type': 'Float', 'value': 2.3}
            )
        
    def test_adding_ovewrite_attribute(self, testcase):
        '''
        Test overwriting an existing attribute
        '''
        float_attr = FloatAttribute(0.01)
        int_attr = IntegerAttribute(3)
        element = self.element_class(
            'some_identifier', 
            {'keyA': float_attr, 'keyB':int_attr}
        )
        element.add_attribute(
            'keyA', 
            {'attribute_type': 'Float', 'value': 2.3},
            overwrite=True
        )
        expected_attr = FloatAttribute(2.3)
        testcase.assertEqual(
            element.attributes['keyA'],
            expected_attr)

    def test_adding_new_attribute(self, testcase):
        '''
        Test adding a new attribute
        '''
        float_attr = FloatAttribute(0.01)
        int_attr = IntegerAttribute(3)
        element = self.element_class(
            'some_identifier', 
            {'keyA': float_attr, 'keyB':int_attr}
        )
        element.add_attribute(
            'keyC', 
            {'attribute_type': 'String', 'value': 'abc'}
        )
        expected_attr = StringAttribute('abc')
        testcase.assertEqual(
            element.attributes['keyC'],
            expected_attr)

        expected_keys = set(['keyA', 'keyB', 'keyC'])
        existing_keys = set(element.attributes.keys())
        testcase.assertTrue(expected_keys == existing_keys)

    def test_adding_bad_attribute_raises_error(self, testcase):
        '''
        Here the attribute has a type in conflict with its
        value.  They key is new, so it COULD be added
        if the value was valid.
        '''
        with testcase.assertRaises(ValidationError):
            testcase.demo_element.add_attribute(
                'keyC', 
                {'attribute_type': 'Integer', 'value': 2.3}
            )


class TestObservation(unittest.TestCase):

    def setUp(self):
        float_attr = FloatAttribute(0.01)
        int_attr = IntegerAttribute(3)
        self.demo_element = Observation(
            'my_identifier', 
            {'keyA': float_attr, 'keyB':int_attr}
        )
        # the class that will execute the tests
        self.tester_class = ElementTester(Observation)

    def test_observation(self):
        test_methods = [x for x in dir(self.tester_class) if x.startswith('test_')]
        for t in test_methods:
            m = getattr(self.tester_class, t)
            m(self)
        
class TestFeature(unittest.TestCase):

    def setUp(self):
        float_attr = FloatAttribute(0.01)
        int_attr = IntegerAttribute(3)
        self.demo_element = Feature(
            'my_identifier', 
            {'keyA': float_attr, 'keyB':int_attr}
        )
        # the class that will execute the tests
        self.tester_class = ElementTester(Feature)

    def test_feature(self):
        test_methods = [x for x in dir(self.tester_class) if x.startswith('test_')]
        for t in test_methods:
            m = getattr(self.tester_class, t)
            m(self)