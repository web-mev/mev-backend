import unittest
import json

from data_structures.observation_set import ObservationSet
from data_structures.feature_set import FeatureSet

from exceptions import NullAttributeError, \
    AttributeValueError, \
    AttributeTypeError, \
    MissingAttributeKeywordError, \
    DataStructureValidationException


class TestElementSet(unittest.TestCase):
    '''
    This tests the creation of the "compound" Element attributes like 
    Observation, Feature

    These types can nest other simple types within them,
    like PositiveIntegerAttribute, etc.
    '''

    def setUp(self):
        # a valid dict representation of a
        # Observation or Feature
        self.element1 = {
            "id": 'ID1',
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

        self.element2 = {
            "id": 'ID2',
            "attributes": {
                "stage": {
                    "attribute_type": "String",
                    "value": "III"
                },
                "age": {
                    "attribute_type": "PositiveInteger",
                    "value": 3
                }        
            }
        }

        self.valid_set = {
            'elements':[
                self.element1,
                self.element2
            ]
        }
        
    def _check_element_set_equality(self, dictA, dictB):
        '''
        A helper method (NOT a test) for assessing whether
        the dict representations are the same. Otherwise, different 
        ordering of the elements in the list (which doesn't matter) can
        cause the self.assertDictEqual method to fail
        '''
        # extracts the 'id' field from the Element instance.
        sorter_func = lambda x: x['value']['id']

        self.assertTrue(dictA['attribute_type'] == dictB['attribute_type'])

        # sort the lists of elements by the 'id' field.
        elementsA = sorted(
            dictA['value']['elements'],
            key = sorter_func
        )
        elementsB = sorted(
            dictB['value']['elements'],
            key = sorter_func
        )
        # now compare the individual dicts. since they are pure
        # dicts and don't contain any interior lists, we can
        # use the assertDictEqual method.
        for itemA, itemB in zip(elementsA, elementsB):
            self.assertDictEqual(itemA, itemB)

    def _creation(self, SetClass, nested_typename):

        # these should work
        
        o = SetClass(self.valid_set)
        dict_rep = o.to_dict()
        # note that the items in the 'elements' key
        # have the usual to_dict representation. This
        # is perhaps redundant info (since ObservationSets
        # can only contain Observation insances), but it 
        # keeps everything consistent.
        set_val = {
            'elements': [
                {
                    'attribute_type': nested_typename,
                    'value': self.element1
                },
                {
                    'attribute_type': nested_typename,
                    'value': self.element2
                }
            ]
        }
        expected_dict = {
            'attribute_type': SetClass.typename,
            'value': set_val
        }
        self._check_element_set_equality(
            dict_rep,
            expected_dict
        )

    def _creation_of_empty_set(self, SetClass, nested_typename):
        o = SetClass({
            'elements': []
        })
        dict_rep = o.to_dict()
        expected_dict = {
            'attribute_type': SetClass.typename, 
            'value': {
                'elements': []
            }
        }
        self.assertDictEqual(dict_rep, expected_dict)

    def test_observation_set_creation(self):
        self._creation(ObservationSet, 'Observation')
        self._creation_of_empty_set(ObservationSet, 'Observation')

    def test_feature_set_creation(self):
        self._creation(FeatureSet, 'Feature')
        self._creation_of_empty_set(FeatureSet, 'Feature')

    def _malformatted_element_tester(self, SetClass):
        '''
        Used to allow testing of both ObservationSet
        and FeatureSet. Tests that the appropriate 
        errors are raised from bad inputs.
        '''
        # This Element (e.g. Observation or Feature)
        # is missing the 'id' key, making it invalid.
        bad_el1 = {
            "attributes": {
                "stage": {
                    "attribute_type": "String",
                    "value": "III"
                },
                "age": {
                    "attribute_type": "PositiveInteger",
                    "value": 3
                }        
            }
        }

        # the nested attribute should cause a failure.
        # We are checking that the reason for the failure
        # is apparent 
        bad_el2 = {
            "id": "ID1",
            "attributes": {
                "stage": {
                    "attribute_type": "PositiveInteger",
                    "value": -3 # <--- BAD
                }        
            }
        }
        # try with a list that is missing the 'elements' key:
        # Note that we just put a bad key...you can't create
        # a native dict like: {[1,2]}
        bad_set1 = {
            'items': [
                self.element1,
                self.element2
            ]
        }
        bad_set2 = {
            'elements': [
                bad_el1
            ]
        }
        bad_set3 = {
            'elements': [
                bad_el2
            ]
        }
        bad_set4 = {
            'elements': 2 #<--- elements should address a list.
        }
        with self.assertRaisesRegex(
            DataStructureValidationException, 'requires an "elements" key'):
            o = SetClass(bad_set1)

        with self.assertRaisesRegex(
            DataStructureValidationException, 'requires an "id" key'):
            o = SetClass(bad_set2)

        with self.assertRaisesRegex(
            DataStructureValidationException, '-3 was not a positive integer'):
            o = SetClass(bad_set3)

        with self.assertRaisesRegex(
            DataStructureValidationException, '"elements" key should address a list'):
            o = SetClass(bad_set4)

    def test_malformatted_elements(self):
        self._malformatted_element_tester(ObservationSet)


    def test_equality(self):
        '''
        We check equality by the set of Element instances
        '''
        # check that ordering doesn't matter
        for t in [ObservationSet, FeatureSet]:
            set1 = self.valid_set
            set2 = {
                'elements': [
                    self.valid_set['elements'][1],
                    self.valid_set['elements'][0]
                ]
            }
            # just double-check that the nested 'elements' lists
            # have the same elements, but in different order.
            self.assertFalse(set1['elements'] == set2['elements'])
            self.assertCountEqual(set1['elements'],set2['elements'])

            t1 = t(set1)
            t2 = t(set2)
            self.assertTrue(t1 == t2)

        # check that they detect inequality when the sets 
        # are NOT equal.
        for t in [ObservationSet, FeatureSet]:
            set1 = self.valid_set
            set2 = {
                'elements': [
                    self.valid_set['elements'][0]
                ]
            }
            # just double-check that the nested 'elements' lists
            # are not the same
            self.assertTrue(len(set1['elements'])==2)
            self.assertTrue(len(set2['elements'])==1)

            t1 = t(set1)
            t2 = t(set2)
            self.assertFalse(t1 == t2)

    # def test_attribute_setter(self):
    #     '''
    #     Test that we can add attributes and that 
    #     poorly formatted attributes fail.
    #     '''
    #     d = {
    #         'id': self.element['id']
    #     }
    #     # this is set up to match the nested attributes
    #     # in self.element so that we can easily check
    #     # that new attributes were properly added
    #     attr_dict = {
    #         "stage": {
    #             "attribute_type": "String",
    #             "value": "IV"
    #         },
    #         "age": {
    #             "attribute_type": "PositiveInteger",
    #             "value": 5
    #         }        
    #     }
    #     x = Observation(d)
    #     x.attributes = attr_dict
    #     dict_rep = x.to_dict()
    #     expected_dict = {
    #         'attribute_type': 'Observation',
    #         'value': self.element
    #     }
    #     self.assertDictEqual(
    #         dict_rep,
    #         expected_dict
    #     )

    #     # test that it will fail if a bad dict is passed:
    #     bad_attr_dict = {
    #         "stage": {
    #             "attribute_type": "BAD TYPE",
    #             "value": "IV"
    #         }       
    #     }
    #     x = Observation(d)
    #     with self.assertRaisesRegex(AttributeTypeError, 'Could not locate type'):
    #         x.attributes = bad_attr_dict 

    # def test_id_setter(self):
    #     '''
    #     Test that we can modify the 'id' field.
    #     '''
    #     d = {
    #         'id': 'foo'
    #     }
    #     x = Observation(d)
    #     self.assertTrue(x.id == 'foo')

    #     # now update:
    #     x.id = 'bar'
    #     self.assertTrue(x.id == 'bar')

    #     dict_rep = x.to_dict()
    #     expected_dict = {
    #         'attribute_type': 'Observation',
    #         'value': {
    #             'id': 'bar',
    #             'attributes': {}
    #         }
    #     }
    #     self.assertDictEqual(
    #         dict_rep,
    #         expected_dict
    #     )

    # def test_add_attribute_to_empty_attributes(self):
    #     '''
    #     Tests the add_attribute method, which
    #     allows us to add additional attribute info
    #     to an existing Observation/Feature.

    #     Add to an instance that does not have any
    #     existing attributes.
    #     '''
    #     # add to an Observation without any attributes
    #     d = {
    #         'id': 'foo'
    #     }
    #     x = Observation(d)
    #     self.assertTrue(x.attributes == {})
    #     new_attr_dict = {
    #         'attribute_type': 'PositiveInteger',
    #         'value': 5
    #     }
    #     x.add_attribute('keyA', new_attr_dict)       
    #     dict_rep = x.to_dict()
    #     expected_dict = {
    #         'attribute_type': 'Observation',
    #         'value': {
    #             'id': 'foo',
    #             'attributes': {
    #                 'keyA': new_attr_dict
    #             }
    #         }        
    #     }
    #     self.assertDictEqual(
    #         dict_rep,
    #         expected_dict
    #     )

    # def test_add_attribute_to_existing_attributes(self):
    #     '''
    #     Tests the add_attribute method, which
    #     allows us to add additional attribute info
    #     to an existing Observation/Feature.

    #     Here we test that we add to the existing
    #     attributes
    #     '''
    #     # an Observation without one attribute, keyA
    #     d = {
    #         'id': 'foo',
    #         'attributes': {
    #             'keyA': {
    #                 'attribute_type':'PositiveInteger',
    #                 'value':5
    #             }
    #         }
    #     }
    #     x = Observation(d)
    #     self.assertTrue(
    #         list(x.attributes.keys()) == ['keyA']
    #     )
    #     new_attr_dict = {
    #         'attribute_type': 'String',
    #         'value': 'abc'
    #     }
    #     x.add_attribute('keyB', new_attr_dict)       
    #     dict_rep = x.to_dict()
    #     expected_dict = {
    #         'attribute_type': 'Observation',
    #         'value': {
    #             'id': 'foo',
    #             'attributes': {
    #                 'keyA': {
    #                     'attribute_type':'PositiveInteger',
    #                     'value':5
    #                 },
    #                 'keyB': new_attr_dict
    #             }
    #         }        
    #     }
    #     self.assertDictEqual(
    #         dict_rep,
    #         expected_dict
    #     )

    # def test_add_duplicate_attribute_fails(self):
    #     '''
    #     Tests the add_attribute method, which
    #     allows us to add additional attribute info
    #     to an existing Observation/Feature.

    #     Test that we can't overwrite an existing 
    #     attribute unless that's explicit.
    #     '''
    #     # add to an Observation with one attribute, keyA
    #     orig_attr_dict = {
    #         'attribute_type':'PositiveInteger',
    #         'value':5
    #     }
    #     d = {
    #         'id': 'foo',
    #         'attributes': {
    #             'keyA': orig_attr_dict
    #         }
    #     }
    #     x = Observation(d)
    #     self.assertTrue(
    #         list(x.attributes.keys()) == ['keyA']
    #     )
    #     # the new attribute- doesn't really matter
    #     # what this is.
    #     new_attr_dict = {
    #         'attribute_type': 'PositiveInteger',
    #         'value': 3
    #     }
    #     # try to assign to keyA. should fail:
    #     with self.assertRaisesRegex(
    #         DataStructureValidationException, 'already existed'):
    #         x.add_attribute('keyA', new_attr_dict)       
    #     dict_rep = x.to_dict()
    #     expected_dict = {
    #         'attribute_type': 'Observation',
    #         'value': {
    #             'id': 'foo',
    #             'attributes': {
    #                 'keyA': orig_attr_dict
    #             }
    #         }        
    #     }
    #     self.assertDictEqual(
    #         dict_rep,
    #         expected_dict
    #     )

    # def test_add_duplicate_attribute_with_overwrite(self):
    #     '''
    #     Tests the add_attribute method, which
    #     allows us to add additional attribute info
    #     to an existing Observation/Feature.

    #     Test that we CAN overwrite an existing 
    #     attribute if we pass the overwrite keyword arg.
    #     '''
    #     # add to an Observation with one attribute, keyA
    #     orig_attr_dict = {
    #         'attribute_type':'PositiveInteger',
    #         'value':5
    #     }
    #     d = {
    #         'id': 'foo',
    #         'attributes': {
    #             'keyA': orig_attr_dict
    #         }
    #     }
    #     x = Observation(d)
    #     self.assertTrue(
    #         list(x.attributes.keys()) == ['keyA']
    #     )
    #     # the new attribute- doesn't really matter
    #     # what this is.
    #     new_attr_dict = {
    #         'attribute_type': 'BoundedInteger',
    #         'value': 3,
    #         'min': 0,
    #         'max': 5
    #     }
    #     # try to assign to keyA. should work since we pass
    #     # the overwrite=True kwarg
    #     x.add_attribute('keyA', new_attr_dict, overwrite=True)       
    #     dict_rep = x.to_dict()
    #     expected_dict = {
    #         'attribute_type': 'Observation',
    #         'value': {
    #             'id': 'foo',
    #             'attributes': {
    #                 'keyA': new_attr_dict
    #             }
    #         }        
    #     }
    #     self.assertDictEqual(
    #         dict_rep,
    #         expected_dict
    #     )

    # def test_respects_null_kwarg(self):
    #     # this is ok:
    #     x = Observation(None, allow_null=True)
    #     dict_rep = x.to_dict()
    #     expected_dict = {
    #         'attribute_type': 'Observation',
    #         'value': None
    #     }
    #     self.assertDictEqual(
    #         dict_rep,
    #         expected_dict
    #     )        

    #     with self.assertRaises(NullAttributeError):
    #         x = Observation(None)