import unittest

from constants import POSITIVE_INF_MARKER

from exceptions import MissingAttributeKeywordError, \
    DataStructureValidationException, \
    NullAttributeError, \
    AttributeTypeError, \
    AttributeValueError

from data_structures.attribute_types import PositiveIntegerAttribute, \
    BoundedFloatAttribute, \
    StringAttribute
from data_structures.list_attributes import StringListAttribute
from data_structures.observation import Observation
from data_structures.observation_set import ObservationSet

from data_structures.attribute_factory import AttributeFactory
from data_structures.simple_attribute_factory import SimpleAttributeFactory


class TestAttributeFactories(unittest.TestCase):

    def _simple_attribute_creation(self, tested_factory):

        # works
        d = {
            'attribute_type': 'PositiveInteger',
            'value': 5
        }
        x = tested_factory(d)
        self.assertTrue(type(x) is PositiveIntegerAttribute)
        self.assertTrue(x.value == 5)

        # works
        d = {
            'attribute_type': 'BoundedFloat',
            'value': 5,
            'min':0,
            'max':10
        }
        x = tested_factory(d)
        self.assertTrue(type(x) is BoundedFloatAttribute)
        self.assertTrue(x.value == 5)

        # works
        d = {
            'attribute_type': 'Float',
            'value': None
        }
        x = tested_factory(d, allow_null=True)
        self.assertIsNone(x.value)

        d = {
            'attribute_type': 'Float',
            'value': POSITIVE_INF_MARKER
        }
        x = tested_factory(d)

        d = {
            'attribute_type': 'Integer',
            'value': POSITIVE_INF_MARKER
        }
        with self.assertRaisesRegex(
            AttributeValueError, 'could not be cast as an integer'):
            x = tested_factory(d)

        # provide a badly-formatted spec. Missing the 'max' key
        d = {
            'attribute_type': 'BoundedFloat',
            'value': 5,
            'min': 0
        }
        with self.assertRaisesRegex(MissingAttributeKeywordError, 'max'):
            x = tested_factory(d)

        # test missing the 'attribute_type' key. Without that, the
        # factory can't determine what type to create
        d = {
            'value':5
        }
        with self.assertRaisesRegex(DataStructureValidationException, 'attribute_type'):
            x = tested_factory(d)

        # missing a value
        d = {
            'attribute_type': 'PositiveInteger',
        }
        with self.assertRaisesRegex(DataStructureValidationException, 'value'):
            x = tested_factory(d)

        # missing a value, but allow_null=True STILL fails.
        d = {
            'attribute_type': 'PositiveInteger',
        }
        with self.assertRaisesRegex(DataStructureValidationException, 'value'):
            x = tested_factory(d, allow_null=True)

        # value is None and allow_null is not specified (False by default)
        d = {
            'attribute_type': 'PositiveInteger',
            'value': None
        }
        with self.assertRaisesRegex(NullAttributeError, 'value'):
            x = tested_factory(d)

        # value is None but allow_null=True permits that.
        d = {
            'attribute_type': 'PositiveInteger',
            'value': None
        }
        x = tested_factory(d, allow_null=True)
        self.assertIsNone(x.value)

        # test the list types:
        mylist = ['a','b','c']
        d = {
            'attribute_type': 'StringList',
            'value': mylist 
        }
        x = tested_factory(d)
        l = [v.value for v in x.value]
        self.assertCountEqual(mylist, l)

        mylist = [1,2,3]
        d = {
            'attribute_type': 'BoundedIntegerList',
            'value': mylist,
            'min': 0,
            'max': 10
        }
        x = tested_factory(d)
        l = [v.value for v in x.value]
        self.assertCountEqual(mylist, l)
        
    def test_simple_attribute_factory(self):
        '''
        We already have tests for the various simple types
        in `test_attributes.py`. Here, we test a subset
        to check that the factory produces what we expect.

        In this test, we use a 'private' method which runs the tests.
        We pass that our SimpleAttributeFactory the ability of that 
        factory to work as expected.
        '''
        self._simple_attribute_creation(SimpleAttributeFactory)

    def test_general_attribute_factory_can_create_simple_types(self):
        '''
        In this test, we use a 'private' method which runs the tests.
        We pass that our AttributeFactory the ability of that 
        factory to work as expected. 
        
        The tested 'general' factory is capable of making
        both simple and "complex" types (like Observation, etc.)
        which can have nested, simple types.

        In this test, we verify that it can indeed create
        simple types
        '''
        self._simple_attribute_creation(AttributeFactory)

    def test_general_factory_can_create_complex_type(self):
        '''
        Since complex types like Observation
        can have nested simple types, we need different factories to avoid
        circular imports.

        Here we test the ability of the factory to create the complex
        types like Observation and ObservationSet
        '''
        # a properly formatted Observation.
        observation_dict = {
            "id": 'MyObs',
            "attributes": {
                "stage": {
                    "attribute_type": "String",
                    "value": "IV"
                },
                "age": {
                    "attribute_type": "PositiveInteger",
                    "value": 5
                }        
            }
        }
        d = {
            'attribute_type': 'Observation',
            'value': observation_dict
        }
        x = AttributeFactory(d)
        self.assertTrue(type(x) is Observation)

        # now try an ObservationSet
        d = {
            'attribute_type': 'ObservationSet',
            'value': {
                'elements': [
                    observation_dict
                ]
            }
        }
        x = AttributeFactory(d)
        self.assertTrue(type(x) is ObservationSet)

    def test_simple_factory_fails_for_complex_type(self):
        '''
        If we attempt to create an Observation with the simple
        factory, it should fail. Since complex types like Observation
        can have nested simple types, we need different factories to avoid
        circular imports.
        '''
        # a properly formatted Observation.
        observation_dict = {
            "id": 'MyObs',
            "attributes": {
                "stage": {
                    "attribute_type": "String",
                    "value": "IV"
                },
                "age": {
                    "attribute_type": "PositiveInteger",
                    "value": 5
                }        
            }
        }
        d = {
            'attribute_type': 'Observation',
            'value': observation_dict
        }
        # just double-check that this passes if we use
        # the correct factory:
        x = AttributeFactory(d)

        # now attempt using the simple factory, which should fail
        with self.assertRaisesRegex(AttributeTypeError, 'Observation'):
            x = SimpleAttributeFactory(d)