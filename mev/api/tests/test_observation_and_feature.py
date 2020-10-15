import unittest
import copy

from rest_framework.exceptions import ValidationError

from api.data_structures import Observation, \
    Feature, \
    IntegerAttribute, \
    FloatAttribute, \
    StringAttribute, \
    BoundedFloatAttribute, \
    BoundedIntegerAttribute, \
    BooleanAttribute
from api.serializers.observation import ObservationSerializer
from api.serializers.feature import FeatureSerializer
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
        data = copy.deepcopy(testcase.demo_element_data)
        element_serializer = self.element_serializer_class(data=data)
        testcase.assertTrue(element_serializer.is_valid())

        element = element_serializer.get_instance()

        # note that equality of Elements is only determined by the 
        # name/identifier.  We will check all the attributes here also.
        testcase.assertEqual(element, testcase.demo_element)
        for attr_name, attr in element.attributes.items():
            expected_attr = testcase.demo_element.attributes[attr_name]
            testcase.assertEqual(expected_attr, attr)

        dd = element.to_dict()
        testcase.assertDictEqual(dd, testcase.demo_element_data)

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
        This tests when the identifier "name" is invalid.
        We ultimately decided, however, to remove the 
        "normalization" of identifiers.

        Still, we keep this test in case we ever want to re-implement
        controls on the naming conventions. In that case, ensure that
        the assert<Bool> call below is correct for the test.
        '''
        data = {'id': 'my-bad-id-', 'attributes':{}}
        element_serializer = self.element_serializer_class(data=data)
        # if we want to impose constraints on the identifier names,
        # then uncomment the line below:
        #testcase.assertFalse(element_serializer.is_valid())
        testcase.assertTrue(element_serializer.is_valid())

    def test_expected_deserialization_case7(self, testcase):
        '''
        Tests a full-featured Observation where one of the attributes
        is a bounded float
        '''
        data = copy.deepcopy(testcase.demo_element_data_w_bounds)
        element_serializer = self.element_serializer_class(data=data)
        testcase.assertTrue(element_serializer.is_valid())
        element = element_serializer.get_instance()

        # note that equality of Observations is only determined by the 
        # name/identifier.  We will check all the attributes here also.
        testcase.assertEqual(element, testcase.demo_element_w_bounds)
        for attr_name, attr in element.attributes.items():
            expected_attr = testcase.demo_element_w_bounds.attributes[attr_name]
            testcase.assertEqual(expected_attr, attr)

        # test that the dictionary representation is valid:
        dd = element.to_dict()
        testcase.assertDictEqual(dd, testcase.demo_element_data_w_bounds)


    def test_expected_deserialization_case8(self, testcase):
        '''
        Tests a full-featured Observation where one of the attributes
        is a bounded float, BUT it is out-of-bounds
        '''
        data = copy.deepcopy(testcase.bad_demo_element_data_w_bounds)
        element_serializer = self.element_serializer_class(data=data)
        testcase.assertFalse(element_serializer.is_valid())

    def test_expected_deserialization_case9(self, testcase):
        '''
        Tests a full-featured Observation where one of the attributes
        is a valid boolean
        '''
        # this version has the "value" of the bool set to True (the python-native boolean)
        expected_result = testcase.demo_element_data_w_bool3 

        data = copy.deepcopy(testcase.demo_element_data_w_bool1)
        element_serializer = self.element_serializer_class(data=data)
        testcase.assertTrue(element_serializer.is_valid())
        testcase.assertDictEqual(element_serializer.data, expected_result)

        data = copy.deepcopy(testcase.demo_element_data_w_bool2)
        element_serializer = self.element_serializer_class(data=data)
        testcase.assertTrue(element_serializer.is_valid())
        testcase.assertDictEqual(element_serializer.data, expected_result)

        data = copy.deepcopy(testcase.demo_element_data_w_bool3)
        element_serializer = self.element_serializer_class(data=data)
        testcase.assertTrue(element_serializer.is_valid())
        testcase.assertDictEqual(element_serializer.data, expected_result)

    def test_expected_deserialization_case10(self, testcase):
        '''
        Tests a full-featured Observation where one of the attributes
        is an INvalid boolean
        '''
        data = copy.deepcopy(testcase.bad_demo_element_data_w_bool)
        element_serializer = self.element_serializer_class(data=data)
        testcase.assertFalse(element_serializer.is_valid())

    def test_expected_deserialization_case11(self, testcase):
        '''
        Tests deserialization with attribute dict that is malformatted
        '''
        data = {'id': 'my_identifier', 'attributes':{'genotype': 'A'}} # genotype key should point at the <Attribute> instance, but instead points at a basic string
        element_serializer = self.element_serializer_class(data=data)
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
        s = self.element_serializer_class(testcase.demo_element_w_bool)
        testcase.assertDictEqual(s.data, testcase.demo_element_data_w_bool3)



class TestObservationSerializer(unittest.TestCase):

    def setUp(self):
        float_attr = FloatAttribute(0.01)
        int_attr = IntegerAttribute(3)
        boolean_attr = BooleanAttribute(True)
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

        self.demo_element_w_bool = Observation(
            'my_identifier', 
            {
                'keyA': int_attr,
                'some_bool': boolean_attr
            }
        )


        self.demo_element_data_w_bool1 = {
            'id': 'my_identifier', 
            'attributes':{
                'keyA': {
                    'attribute_type':'Integer', 
                    'value': 3
                },
                'some_bool':{
                    'attribute_type':'Boolean', 
                    'value': 'true'
                }
            }
        }

        self.demo_element_data_w_bool2 = {
            'id': 'my_identifier', 
            'attributes':{
                'keyA': {
                    'attribute_type':'Integer', 
                    'value': 3
                },
                'some_bool':{
                    'attribute_type':'Boolean', 
                    'value': 1
                }
            }
        }

        self.demo_element_data_w_bool3 = {
            'id': 'my_identifier', 
            'attributes':{
                'keyA': {
                    'attribute_type':'Integer', 
                    'value': 3
                },
                'some_bool':{
                    'attribute_type':'Boolean', 
                    'value': True
                }
            }
        }

        self.bad_demo_element_data_w_bool = {
            'id': 'my_identifier', 
            'attributes':{
                'keyA': {
                    'attribute_type':'Integer', 
                    'value': 3
                },
                'some_bool':{
                    'attribute_type':'Boolean', 
                    'value': -1
                }
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
        boolean_attr = BooleanAttribute(True)
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

        self.demo_element_w_bool = Feature(
            'my_identifier', 
            {
                'keyA': int_attr,
                'some_bool': boolean_attr
            }
        )

        self.demo_element_data_w_bool1 = {
            'id': 'my_identifier', 
            'attributes':{
                'keyA': {
                    'attribute_type':'Integer', 
                    'value': 3
                },
                'some_bool':{
                    'attribute_type':'Boolean', 
                    'value': 'true'
                }
            }
        }

        self.demo_element_data_w_bool2 = {
            'id': 'my_identifier', 
            'attributes':{
                'keyA': {
                    'attribute_type':'Integer', 
                    'value': 3
                },
                'some_bool':{
                    'attribute_type':'Boolean', 
                    'value': 1
                }
            }
        }

        self.demo_element_data_w_bool3 = {
            'id': 'my_identifier', 
            'attributes':{
                'keyA': {
                    'attribute_type':'Integer', 
                    'value': 3
                },
                'some_bool':{
                    'attribute_type':'Boolean', 
                    'value': True
                }
            }
        }

        self.bad_demo_element_data_w_bool = {
            'id': 'my_identifier', 
            'attributes':{
                'keyA': {
                    'attribute_type':'Integer', 
                    'value': 3
                },
                'some_bool':{
                    'attribute_type':'Boolean', 
                    'value': -1
                }
            }
        }
        # the class that will execute the tests
        self.tester_class = ElementSerializerTester(FeatureSerializer)

    def test_feature_serializer(self):
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