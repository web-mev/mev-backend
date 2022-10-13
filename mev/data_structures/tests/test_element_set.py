from copy import deepcopy
import unittest

from data_structures.observation_set import ObservationSet
from data_structures.feature_set import FeatureSet
from data_structures.observation import Observation
from data_structures.feature import Feature

from exceptions import NullAttributeError, \
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

        # check the simplified representation also:
        simple_dict_rep = o.to_simple_dict()
        self.assertCountEqual(
            simple_dict_rep['elements'], self.valid_set['elements'])


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

    def _element_setter(self, SetClass, nested_element_type):
        '''
        Test that the setter for the element
        class member works as expected. This method
        is used to test both ObservationSet/FeatureSet
        '''
        el_set = SetClass(self.valid_set)
        elements = el_set.elements
        self.assertCountEqual(
            elements,
            [
                nested_element_type(self.element1),
                nested_element_type(self.element2)
            ]
        )

        # now try resetting. It should completely change
        element3 = {
            "id": 'ID3',
            "attributes": {}
        }
        el_set.elements = [element3]
        self.assertCountEqual(
            el_set.elements,
            [
                nested_element_type(element3),
            ]
        )

        # try setting to empty set:
        el_set.elements = []
        self.assertCountEqual(
            el_set.elements,
            []
        )

        # attempt to reset with something that is invalid.
        # Should keep it unchanged
        el_set = SetClass(self.valid_set)
        # this is missing the 'id' key:
        element4 = {
            "attributes": {}
        }
        with self.assertRaisesRegex(
            DataStructureValidationException, 'requires an "id" key'):
            el_set.elements = [element4]
        # check that the elements are unchanged:
        self.assertCountEqual(
            elements,
            [
                nested_element_type(self.element1),
                nested_element_type(self.element2)
            ]
        )
    def test_element_setter(self):
        self._element_setter(ObservationSet, Observation)
        self._element_setter(FeatureSet, Feature)

    def _add_to_empty(self, SetClass, nested_element_type):
        '''
        Check that a new element can be added to an ElementSet
        that has no members. This method is used by the actual
        class to test both types of ElementSet
        '''
        element_set = SetClass({'elements':[]})
        element_dict = {
            "id": 'ID3',
            "attributes": {}
        }
        element_set.add_element(element_dict)
        self.assertCountEqual(
            element_set.elements,
            [
                nested_element_type(element_dict),
            ]
        )

    def test_add_element_to_empty_set(self):
        '''
        Tests the add_element method, which
        allows us to append additional elements
        to an existing ObservationSet/FeatureSet.

        Add to an instance that does not have any
        existing elements
        '''
        self._add_to_empty(ObservationSet, Observation)
        self._add_to_empty(FeatureSet, Feature)

    def _add_to_existing(self, SetClass, nested_element_type):
        '''
        Check that a new element can be added to an ElementSet
        that has some members. This method is used by the actual
        class to test both types of ElementSet
        '''
        element_set = SetClass({
                'elements':[
                    self.element1
                ]
            }
        )
        element_dict = {
            "id": 'ID3',
            "attributes": {}
        }
        element_set.add_element(element_dict)
        self.assertCountEqual(
            element_set.elements,
            [
                nested_element_type(self.element1),
                nested_element_type(element_dict),
            ]
        )

    def test_add_element_to_existing_set(self):
        '''
        Tests the add_element method, which
        allows us to append additional elements
        to an existing ObservationSet/FeatureSet.

        Add to an instance that does not have any
        existing elements
        '''
        self._add_to_existing(ObservationSet, Observation)
        self._add_to_existing(FeatureSet, Feature)

    def _add_duplicate(self, SetClass, nested_element_type):
        '''
        Check that addition of a duplicated element does not
        change the ElementSet.
        This method is used by the actual
        class to test both types of ElementSet
        '''
        element_set = SetClass({
                'elements':[
                    self.element1,
                    self.element2
                ]
            }
        )
        element_set.add_element(self.element1)
        self.assertCountEqual(
            element_set.elements,
            [
                nested_element_type(self.element1),
                nested_element_type(self.element2),
            ]
        )

    def test_add_duplicate_element(self):
        '''
        Tests the add_element method, which
        allows us to append additional elements
        to an existing ObservationSet/FeatureSet.

        Add an element that already exists. should not
        change the set.
        '''
        self._add_to_existing(ObservationSet, Observation)
        self._add_to_existing(FeatureSet, Feature)

    def _respects_null_kwarg(self, SetClass):
        '''
        Allows us to test for both types of ElementSet
        '''
        # this is ok:
        x = SetClass(None, allow_null=True)
        dict_rep = x.to_dict()
        expected_dict = {
            'attribute_type': SetClass.typename,
            'value': None
        }
        self.assertDictEqual(
            dict_rep,
            expected_dict
        )        

        with self.assertRaises(NullAttributeError):
            x = SetClass(None)

    def test_respects_null_kwarg(self):
        self._respects_null_kwarg(ObservationSet)
        self._respects_null_kwarg(FeatureSet)


    def _reject_duplicate_elements(self, SetClass):
        '''
        Runs the tests for `test_rejects_duplicate_elements`
        so we can test both class types more easily.
        '''
        with self.assertRaisesRegex(DataStructureValidationException, 'duplicate entry'):
            element_set = SetClass({
                'elements':[
                        {'id': 'foo'},
                        {'id': 'foo'}
                    ]
                }
            )

    def test_rejects_duplicate_elements(self):
        '''
        Rather than silently ignore duplicate elements, 
        check that we raise an exception
        '''
        self._reject_duplicate_elements(ObservationSet)
        self._reject_duplicate_elements(FeatureSet)


    def _equality_test(self, SetClass):
        '''
        Tests the equality and equivalency of ElementSet.
        '''
        element_set1 = SetClass({
            'elements':[
                self.element1,
                self.element2
            ]
        })
        element_set2 = SetClass({
            'elements':[
                self.element2,
                self.element1
            ]
        })
        self.assertTrue(element_set1 == element_set2)

        element_set1.is_equivalent_to(element_set2)

    def test_equality_operator(self):
        self._equality_test(ObservationSet)
        self._equality_test(FeatureSet)

    def _intersection_test(self, SetClass, nested_type):
        element_set1 = SetClass({
            'elements':[
                self.element1,
                self.element2
            ]
        })
        element_set2 = SetClass({
            'elements':[
                self.element1
            ]
        })
        intersection_set = element_set1.set_intersection(element_set2)
        self.assertCountEqual(
            intersection_set.elements,
            [
                nested_type(self.element1)
            ]
        )

        # intersect two sets that have complementary info.
        # The attributes dict have different info which we combine
        comp_element = deepcopy(self.element1)
        # change the "stage" attribute from "IV" to "foo":
        comp_element['attributes']['other'] = {
            'attribute_type': 'Float',
            'value': 0.5
        }
        element_set2 = SetClass({
            'elements':[
                comp_element
            ]
        })
        intersection_set = element_set1.set_intersection(element_set2)
        dict_rep = intersection_set.to_dict()
        expected_dict = {
            'attribute_type': SetClass.typename,
            'value': {
                'elements': [
                    {
                        'attribute_type': nested_type.typename,
                        'value': {
                            "id": 'ID1',
                            "attributes": {
                                "stage": {
                                    "attribute_type": "String",
                                    "value": "IV"
                                },
                                "age": {
                                    "attribute_type": "PositiveInteger",
                                    "value": 5
                                },
                                "other": {
                                    'attribute_type': 'Float',
                                    'value': 0.5
                                }      
                            }
                        }
                    }
                ]
            }
        }
        self._check_element_set_equality(dict_rep, expected_dict)

        # intersect two sets with no common elements:
        element_set1 = SetClass({
            'elements':[
                self.element1,
            ]
        })
        element_set2 = SetClass({
            'elements':[
                self.element2
            ]
        })
        intersection_set = element_set1.set_intersection(element_set2)
        # the intersection should be empty:
        self.assertCountEqual(
            intersection_set.elements,
            []
        )

        # intersect two sets that have conflicting info.
        element_set1 = SetClass({
            'elements':[
                self.element1,
                self.element2
            ]
        })
        conflicting_element = deepcopy(self.element1)
        # change the "stage" attribute from "IV" to "foo":
        conflicting_element['attributes']['stage']['value'] = 'foo'
        element_set2 = SetClass({
            'elements':[
                conflicting_element,
                self.element2
            ]
        })
        with self.assertRaisesRegex(
            DataStructureValidationException, 'conflict in the attributes'):
            intersection_set = element_set1.set_intersection(element_set2)

    def test_set_intersection(self):
        self._intersection_test(ObservationSet, Observation)
        self._intersection_test(FeatureSet, Feature)

    def _union_test(self, SetClass, nested_type):
        element_set1 = SetClass({
            'elements':[
                self.element1,
                self.element2
            ]
        })
        element_set2 = SetClass({
            'elements':[
                self.element1
            ]
        })
        union_set = element_set1.set_union(element_set2)
        self.assertCountEqual(
            union_set.elements,
            [
                nested_type(self.element1),
                nested_type(self.element2)
            ]
        )

        # Get the union of two sets where one element has complementary info.
        # The attributes dict have different info which we combine
        comp_element = deepcopy(self.element1)
        # change the "stage" attribute from "IV" to "foo":
        comp_element['attributes']['other'] = {
            'attribute_type': 'Float',
            'value': 0.5
        }
        element_set2 = SetClass({
            'elements':[
                comp_element
            ]
        })
        # In this union element_set1 has element1, element2.
        # element_set2 has a slight, complementary/allowable
        # modification to element1. Hence, the union should have
        # the 'augmented' element1 AND element2
        union_set = element_set1.set_union(element_set2)
        dict_rep = union_set.to_dict()
        expected_dict = {
            'attribute_type': SetClass.typename,
            'value': {
                'elements': [
                    {
                        'attribute_type': nested_type.typename,
                        'value': {
                            "id": 'ID1',
                            "attributes": {
                                "stage": {
                                    "attribute_type": "String",
                                    "value": "IV"
                                },
                                "age": {
                                    "attribute_type": "PositiveInteger",
                                    "value": 5
                                },
                                "other": {
                                    'attribute_type': 'Float',
                                    'value': 0.5
                                }      
                            }
                        }
                    },
                    {
                        'attribute_type': nested_type.typename,
                        'value': {
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
                    }
                ]
            }
        }
        self._check_element_set_equality(dict_rep, expected_dict)

        # union of two sets with no common elements:
        element_set1 = SetClass({
            'elements':[
                self.element1,
            ]
        })
        element_set2 = SetClass({
            'elements':[
                self.element2
            ]
        })
        union_set = element_set1.set_union(element_set2)
        # the union should be empty:
        self.assertCountEqual(
            union_set.elements,
            [
                nested_type(self.element1),
                nested_type(self.element2)
            ]
        )

        # union of two sets where one of the elements has conflicting
        # info.
        element_set1 = SetClass({
            'elements':[
                self.element1,
                self.element2
            ]
        })
        conflicting_element = deepcopy(self.element1)
        # change the "stage" attribute from "IV" to "foo":
        conflicting_element['attributes']['stage']['value'] = 'foo'
        element_set2 = SetClass({
            'elements':[
                conflicting_element,
                self.element2
            ]
        })
        with self.assertRaisesRegex(
            DataStructureValidationException, 'conflict in the attributes'):
            union_set = element_set1.set_union(element_set2)

    def test_set_union(self):
        self._union_test(ObservationSet, Observation)
        self._union_test(FeatureSet, Feature)

    def _difference_test(self, SetClass, nested_type):

        # test a true difference in sets
        element_set1 = SetClass({
            'elements':[
                self.element1,
                self.element2
            ]
        })
        element_set2 = SetClass({
            'elements':[
                self.element1
            ]
        })
        diff_set = element_set1.set_difference(element_set2)
        self.assertCountEqual(
            diff_set.elements,
            [
                nested_type(self.element2)
            ]
        )

        # test difference of equivalent sets
        element_set1 = SetClass({
            'elements':[
                self.element1,
            ]
        })
        element_set2 = SetClass({
            'elements':[
                self.element1
            ]
        })
        diff_set = element_set1.set_difference(element_set2)
        self.assertCountEqual(
            diff_set.elements,
            []
        )

        # test difference when compared against empty set
        element_set1 = SetClass({
            'elements':[
                self.element1,
            ]
        })
        element_set2 = SetClass({
            'elements':[]
        })
        diff_set = element_set1.set_difference(element_set2)
        self.assertCountEqual(
            diff_set.elements,
            [
                nested_type(self.element1)
            ]
        )

        # test the difference where a common
        # element has differing attributes.
        # Should ignore those differences
        # and remove it.
        element_set1 = SetClass({
            'elements':[
                self.element1,
                self.element2
            ]
        })
        el = deepcopy(self.element1)
        el['attributes']['other'] = {
            'attribute_type': 'Float',
            'value': 0.5
        }
        element_set2 = SetClass({
            'elements':[
                el
            ]
        })
        diff_set = element_set1.set_difference(element_set2)
        self.assertCountEqual(
            diff_set.elements,
            [
                nested_type(self.element2)
            ]
        )
        
    def test_set_difference(self):
        self._difference_test(ObservationSet, Observation)
        self._difference_test(FeatureSet, Feature)

    def _sub_and_superset_methods_test(self, SetClass):

        element_set1 = SetClass({
            'elements':[
                self.element1,
                self.element2
            ]
        })
        element_set2 = SetClass({
            'elements':[
                self.element1
            ]
        })
        # modify element1 so the attributes are not 
        # exactly the same.
        el = deepcopy(self.element1)
        el['attributes']['other'] = {
            'attribute_type': 'Float',
            'value': 0.5
        }        
        element_set3 = SetClass({
            'elements':[
                el,
                self.element2
            ]
        }) 
        self.assertTrue(element_set1.is_proper_superset_of(element_set2))
        self.assertTrue(element_set2.is_proper_subset_of(element_set1))
        self.assertFalse(element_set1.is_proper_superset_of(element_set3))
        self.assertFalse(element_set3.is_proper_subset_of(element_set1))

    def test_sub_and_superset_methods(self):
        self._sub_and_superset_methods_test(ObservationSet)        
        self._sub_and_superset_methods_test(FeatureSet)

    def _extra_keys_test(self, SetClass):
        with self.assertRaisesRegex(DataStructureValidationException, 'extra'):
            SetClass({
                'elements': [],
                'multiple': True
            })
        # it's ok to have extra keys if the proper 
        # kwarg is passed.
        SetClass({
            'elements': [],
            'multiple': True
        }, ignore_extra_keys=True)

    def test_extra_keys(self):
        '''
        Tests that extra keys cause an exception
        to be raised, UNLESS the `ignore_extra_keys` 
        kwarg is passed
        '''
        self._extra_keys_test(ObservationSet)        
        self._extra_keys_test(FeatureSet)

    def _permit_null_attributes_in_elements_test(self, SetClass):
        '''
        Runs the test for both Obs/FeatureSet

        This allows us to create Obs/FeatureSets that
        have nested elements (Observation/Feature) which
        can have null values if passed the
        permit_null_attributes keyword arg 

        This is important for ingesting metadata from
        annotation files where we may encounter some missing
        data
        '''
        el1 = {
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

        el2 = {
            "id": 'ID2',
            "attributes": {
                "stage": {
                    "attribute_type": "String",
                    # without permit_null_attributes=True,
                    # this would cause the validation to fail
                    "value": None
                },
                "age": {
                    "attribute_type": "PositiveInteger",
                    "value": 3
                }        
            }
        }

        el_set = {
            'elements':[
                el1,
                el2
            ]
        }
        x = SetClass(el_set, permit_null_attributes=True)
        with self.assertRaises(NullAttributeError):
            x = SetClass(el_set)

    def test_permit_null_attributes_in_elements(self):
        self._permit_null_attributes_in_elements_test(ObservationSet)
        self._permit_null_attributes_in_elements_test(FeatureSet)