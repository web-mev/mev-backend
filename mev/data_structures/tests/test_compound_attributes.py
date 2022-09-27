import unittest
from copy import deepcopy

from data_structures.observation import Observation
from data_structures.feature import Feature

from exceptions import NullAttributeError, \
    AttributeValueError, \
    AttributeTypeError, \
    MissingAttributeKeywordError, \
    DataStructureValidationException


class TestElement(unittest.TestCase):
    '''
    This tests the creation of the "compound" Element attributes like 
    Observation, Feature

    These types can nest other simple types within them,
    like PositiveIntegerAttribute, etc.
    '''

    def setUp(self):
        # a valid dict representation of a
        # Observation or Feature
        self.element = {
            "id": 'ID',
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
        
    def test_creation(self):
        # these should just work
        o = Observation(self.element)
        dict_rep = o.to_dict()

        expected_dict = {
            'attribute_type': 'Observation',
            'value': self.element
        }
        self.assertDictEqual(
            dict_rep,
            expected_dict
        )

        f = Feature(self.element)
        dict_rep = f.to_dict()
        expected_dict = {
            'attribute_type': 'Feature',
            'value': self.element
        }
        self.assertDictEqual(
            dict_rep,
            expected_dict
        )

        # test that we can pass a dict
        # containing only the 'id' and
        # an empty 'attributes' dict will
        # be added.
        o = Observation({'id': 'foo'})
        dict_rep = o.to_dict()
        expected_dict = {
            'attribute_type': 'Observation',
            'value': {
                'id': 'foo',
                'attributes': {}
            }
        }
        self.assertDictEqual(
            dict_rep,
            expected_dict
        )

    def test_basic_creation_failures(self):
        # test that we need to pass a dict:
        with self.assertRaisesRegex(
            DataStructureValidationException, 'expects a dictionary'):
            o = Observation('foo')

        # test that we need to pass at least an 'id' field in the dict:
        with self.assertRaisesRegex(
            DataStructureValidationException, 'requires an "id" key'):
            o = Observation({})

        # we are strict-- do NOT accept unexpected keys
        with self.assertRaisesRegex(DataStructureValidationException, 'extra keys'):
            o = Observation({'id':'foo', 'other':3})

    def test_fails_with_bad_id(self):

        d =  {
            "id": '9',
            "attributes": {}        
        }
        # an exception is raised that should mention
        # that the 'stage' attribute is bad
        for t in [Observation, Feature]:
            with self.assertRaisesRegex(
                AttributeValueError, 'did not match the naming requirements'):
                t(d)

    def test_fails_with_bad_attributes(self):
        d = {
            "id": 'ID',
            "attributes": {
                # don't allow passing of an empty 'attribute'
                "stage": {}        
            }
        }
        # an exception is raised that should mention
        # that the 'stage' attribute is bad
        for t in [Observation, Feature]:
            with self.assertRaisesRegex(
                DataStructureValidationException, 'stage'):
                t(d)

        d = {
            "id": 'ID',
            "attributes": {
                "stage": {
                    # missing the 'value' key
                    "attribute_type": "String"
                }        
            }
        }
        # an exception is raised that should mention
        # that the 'stage' attribute is bad
        for t in [Observation, Feature]:
            with self.assertRaisesRegex(
                DataStructureValidationException, 'stage'):
                t(d)

        d = {
            "id": 'ID',
            "attributes": {
                "stage": {
                    "attribute_type": "PositiveInteger",
                    "value": -3 # BAD- not positive
                }        
            }
        }
        # an exception is raised that should mention
        # that the 'stage' attribute is bad
        for t in [Observation, Feature]:
            with self.assertRaisesRegex(
                DataStructureValidationException, 'stage.*not a positive integer'):
                t(d)

        d = {
            "id": 'ID',
            "attributes": {
                "stage": {
                    "attribute_type": "BoundedInteger",
                    "value": 5,
                    "min": 0
                    # missing 'max'
                }        
            }
        }
        # an exception is raised that should mention
        # that the 'stage' attribute is bad
        for t in [Observation, Feature]:
            with self.assertRaisesRegex(
                MissingAttributeKeywordError, 'max'):
                t(d)

    def test_equality(self):
        '''
        We only check equality by the identifier
        '''
        for t in [Observation, Feature]:
            t1 = t(self.element)
            # create another dict that contains the same 'id' key,
            # despite having no attributes.
            other = {
                'id': self.element['id']
            }
            t2 = t(other)
            self.assertTrue(t1 == t2)

    def test_attribute_setter(self):
        '''
        Test that we can add attributes and that 
        poorly formatted attributes fail.
        '''
        d = {
            'id': self.element['id']
        }
        # this is set up to match the nested attributes
        # in self.element so that we can easily check
        # that new attributes were properly added
        attr_dict = {
            "stage": {
                "attribute_type": "String",
                "value": "IV"
            },
            "age": {
                "attribute_type": "PositiveInteger",
                "value": 5
            }        
        }
        x = Observation(d)
        x.attributes = attr_dict
        dict_rep = x.to_dict()
        expected_dict = {
            'attribute_type': 'Observation',
            'value': self.element
        }
        self.assertDictEqual(
            dict_rep,
            expected_dict
        )

        # test that it will fail if a bad dict is passed:
        bad_attr_dict = {
            "stage": {
                "attribute_type": "BAD TYPE",
                "value": "IV"
            }       
        }
        x = Observation(d)
        with self.assertRaisesRegex(AttributeTypeError, 'Could not locate type'):
            x.attributes = bad_attr_dict 

    def test_id_setter(self):
        '''
        Test that we can modify the 'id' field.
        '''
        d = {
            'id': 'foo'
        }
        x = Observation(d)
        self.assertTrue(x.id == 'foo')

        # now update:
        x.id = 'bar'
        self.assertTrue(x.id == 'bar')

        dict_rep = x.to_dict()
        expected_dict = {
            'attribute_type': 'Observation',
            'value': {
                'id': 'bar',
                'attributes': {}
            }
        }
        self.assertDictEqual(
            dict_rep,
            expected_dict
        )

    def test_add_attribute_to_empty_attributes(self):
        '''
        Tests the add_attribute method, which
        allows us to add additional attribute info
        to an existing Observation/Feature.

        Add to an instance that does not have any
        existing attributes.
        '''
        # add to an Observation without any attributes
        d = {
            'id': 'foo'
        }
        x = Observation(d)
        self.assertTrue(x.attributes == {})
        new_attr_dict = {
            'attribute_type': 'PositiveInteger',
            'value': 5
        }
        x.add_attribute('keyA', new_attr_dict)       
        dict_rep = x.to_dict()
        expected_dict = {
            'attribute_type': 'Observation',
            'value': {
                'id': 'foo',
                'attributes': {
                    'keyA': new_attr_dict
                }
            }        
        }
        self.assertDictEqual(
            dict_rep,
            expected_dict
        )

    def test_add_attribute_to_existing_attributes(self):
        '''
        Tests the add_attribute method, which
        allows us to add additional attribute info
        to an existing Observation/Feature.

        Here we test that we add to the existing
        attributes
        '''
        # an Observation without one attribute, keyA
        d = {
            'id': 'foo',
            'attributes': {
                'keyA': {
                    'attribute_type':'PositiveInteger',
                    'value':5
                }
            }
        }
        x = Observation(d)
        self.assertTrue(
            list(x.attributes.keys()) == ['keyA']
        )
        new_attr_dict = {
            'attribute_type': 'String',
            'value': 'abc'
        }
        x.add_attribute('keyB', new_attr_dict)       
        dict_rep = x.to_dict()
        expected_dict = {
            'attribute_type': 'Observation',
            'value': {
                'id': 'foo',
                'attributes': {
                    'keyA': {
                        'attribute_type':'PositiveInteger',
                        'value':5
                    },
                    'keyB': new_attr_dict
                }
            }        
        }
        self.assertDictEqual(
            dict_rep,
            expected_dict
        )

    def test_add_duplicate_attribute_fails(self):
        '''
        Tests the add_attribute method, which
        allows us to add additional attribute info
        to an existing Observation/Feature.

        Test that we can't overwrite an existing 
        attribute unless that's explicit.
        '''
        # add to an Observation with one attribute, keyA
        orig_attr_dict = {
            'attribute_type':'PositiveInteger',
            'value':5
        }
        d = {
            'id': 'foo',
            'attributes': {
                'keyA': orig_attr_dict
            }
        }
        x = Observation(d)
        self.assertTrue(
            list(x.attributes.keys()) == ['keyA']
        )
        # the new attribute- doesn't really matter
        # what this is.
        new_attr_dict = {
            'attribute_type': 'PositiveInteger',
            'value': 3
        }
        # try to assign to keyA. should fail:
        with self.assertRaisesRegex(
            DataStructureValidationException, 'already existed'):
            x.add_attribute('keyA', new_attr_dict)       
        dict_rep = x.to_dict()
        expected_dict = {
            'attribute_type': 'Observation',
            'value': {
                'id': 'foo',
                'attributes': {
                    'keyA': orig_attr_dict
                }
            }        
        }
        self.assertDictEqual(
            dict_rep,
            expected_dict
        )

    def test_add_duplicate_attribute_with_overwrite(self):
        '''
        Tests the add_attribute method, which
        allows us to add additional attribute info
        to an existing Observation/Feature.

        Test that we CAN overwrite an existing 
        attribute if we pass the overwrite keyword arg.
        '''
        # add to an Observation with one attribute, keyA
        orig_attr_dict = {
            'attribute_type':'PositiveInteger',
            'value':5
        }
        d = {
            'id': 'foo',
            'attributes': {
                'keyA': orig_attr_dict
            }
        }
        x = Observation(d)
        self.assertTrue(
            list(x.attributes.keys()) == ['keyA']
        )
        # the new attribute- doesn't really matter
        # what this is.
        new_attr_dict = {
            'attribute_type': 'BoundedInteger',
            'value': 3,
            'min': 0,
            'max': 5
        }
        # try to assign to keyA. should work since we pass
        # the overwrite=True kwarg
        x.add_attribute('keyA', new_attr_dict, overwrite=True)       
        dict_rep = x.to_dict()
        expected_dict = {
            'attribute_type': 'Observation',
            'value': {
                'id': 'foo',
                'attributes': {
                    'keyA': new_attr_dict
                }
            }        
        }
        self.assertDictEqual(
            dict_rep,
            expected_dict
        )