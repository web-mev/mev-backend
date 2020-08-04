import unittest

from rest_framework.exceptions import ValidationError

from api.data_structures import Observation, \
    ObservationSet, \
    Feature, \
    FeatureSet, \
    StringAttribute

from api.serializers.observation import ObservationSerializer
from api.serializers.observation_set import ObservationSetSerializer
from api.serializers.feature import FeatureSerializer
from api.serializers.feature_set import FeatureSetSerializer

class ElementSetTester(object):
    '''
    The idea here is that we have very similar "base"
    behavior for ObservationSet, FeatureSet, and possibly any other
    derived classes of ElementSet.  This allows me to "inject" the 
    proper class and test that without re-writing all the same tests.
    '''

    def __init__(self, element_set_class):
        self.element_set_class = element_set_class

    def test_create_element_set(self, testcase):
        element_list = [testcase.el1, testcase.el2]
        el_set = self.element_set_class(element_list, True)
        testcase.assertEqual(
            el_set.elements, 
            set([testcase.el1, testcase.el2])
        )
        # test without setting the explicit arg for multiple:
        element_set = self.element_set_class(element_list)
        testcase.assertEqual(
            element_set.elements, 
            set([testcase.el1, testcase.el2])
        )

    def test_create_singleton_element_set(self, testcase):
        element_list = [testcase.el1, testcase.el2]
        with testcase.assertRaises(ValidationError):
            element_set = self.element_set_class(element_list, False)

    def test_duplicate_element_rejected_on_creation(self, testcase):
        element_list = [testcase.el1, testcase.duplicate_element]
        with testcase.assertRaises(ValidationError):
            element_set = self.element_set_class(element_list)

    def test_raises_exception_on_duplicate_add(self, testcase):
        element_list = [testcase.el1, testcase.el2]
        element_set = self.element_set_class(element_list)
        with testcase.assertRaises(ValidationError):
            element_set.add_element(testcase.duplicate_element)

    def test_element_set_equality(self, testcase):
        element_list1 = [testcase.el1, testcase.el2]
        element_list2 = [testcase.duplicate_element, testcase.el2]
        element_set1 = self.element_set_class(element_list1)  
        element_set2 = self.element_set_class(element_list2)  
        testcase.assertEqual(element_set1, element_set2)
    
    def test_element_set_equivalence(self, testcase):
        element_list1 = [testcase.el1, testcase.el2]
        element_list2 = [testcase.duplicate_element, testcase.el2]
        element_set1 = self.element_set_class(element_list1)  
        element_set2 = self.element_set_class(element_list2)  
        testcase.assertTrue(element_set1.is_equivalent_to(element_set2))

    def test_element_superset(self, testcase):
        element_list1 = [testcase.el1, testcase.el2]
        element_list2 = [testcase.el2]
        element_set1 = self.element_set_class(element_list1)  
        element_set2 = self.element_set_class(element_list2)  
        testcase.assertTrue(element_set1.is_proper_superset_of(element_set2))

    def test_element_subset(self, testcase):
        element_list1 = [testcase.el1, testcase.el2]
        element_list2 = [testcase.el2]
        element_set1 = self.element_set_class(element_list1)  
        element_set2 = self.element_set_class(element_list2)  
        testcase.assertTrue(element_set2.is_proper_subset_of(element_set1))

    def test_set_difference(self, testcase):
        element_list1 = [testcase.el1, testcase.el2]
        element_list2 = [testcase.el2]
        element_set1 = self.element_set_class(element_list1)  
        element_set2 = self.element_set_class(element_list2)  
        diff_set = element_set1.set_difference(element_set2)
        testcase.assertEqual(len(diff_set), 1)
        testcase.assertEqual(diff_set, set([testcase.el1]))

    def test_set_intersection(self, testcase):
        element_list1 = [testcase.el1, testcase.el2]
        element_list2 = [testcase.el2]
        element_set1 = self.element_set_class(element_list1)  
        element_set2 = self.element_set_class(element_list2)  
        int_set = element_set1.set_intersection(element_set2)
        testcase.assertEqual(len(int_set), 1)
        testcase.assertEqual(int_set, set([testcase.el2]))


class TestObservationSet(unittest.TestCase):

    def setUp(self):
        # create a couple Observations to use
        self.el1 = Observation('sampleA', {
            'phenotype': StringAttribute('WT')
        })

        self.el2 = Observation('sampleB', {
            'phenotype': StringAttribute('KO')
        })

        # a duplicate of element above:
        self.duplicate_element = Observation('sampleA', {})

        # instantiate the class that will actually execute the tests
        self.tester_class = ElementSetTester(ObservationSet)


    def test_observationset(self):
        '''
        This calls all the methods that start with "test_" in the testing class above.
        It hands that class an instance of "self", which is a unittest.TestCase instance
        which allows that class to use the elements created in the setUp method.
        '''
        test_methods = [x for x in dir(self.tester_class) if x.startswith('test_')]
        for t in test_methods:
            m = getattr(self.tester_class, t)
            m(self)


class TestFeatureSet(unittest.TestCase):

    def setUp(self):
        # create a couple Featires to use
        self.el1 = Feature('geneA', {
            'oncogene': StringAttribute('Y')
        })

        self.el2 = Feature('sampleB', {
            'oncogene': StringAttribute('N')
        })

        # a duplicate of element above:
        self.duplicate_element = Feature('geneA', {})

        # instantiate the class that will actually execute the tests
        self.tester_class = ElementSetTester(FeatureSet)


    def test_featureset(self):
        test_methods = [x for x in dir(self.tester_class) if x.startswith('test_')]
        for t in test_methods:
            m = getattr(self.tester_class, t)
            m(self)


class ElementSetSerializerTester(object):
    '''
    The idea here is that we have very similar "base"
    behavior for ObservationSetSerializer, FeatureSetSerializer, 
    and possibly any other derived classes of ElementSetSerializer.
    This allows me to "inject" the proper class and test that 
    without re-writing all the same tests.
    '''

    def __init__(self, element_set_serializer_class):
        self.element_set_serializer_class = element_set_serializer_class

    def test_serialization(self, testcase):

        serialzed_element_set = self.element_set_serializer_class(testcase.element_set)

        # to test equality, we have to convert from a list of OrderedDict to 
        # a list of native dict:
        new_list = []
        for o in serialzed_element_set.data['elements']:
            new_list.append(dict(o))
        new_list = sorted(new_list, key=lambda x:x['id'])

        # assert equality of the lists
        testcase.assertListEqual(
            new_list, 
            testcase.expected_element_set_data['elements'])
        testcase.assertEqual(
            testcase.expected_element_set_data['multiple'],
            serialzed_element_set.data['multiple']
        )

    def test_deserialization(self, testcase):
        '''
        This tests that the deserialization happens 
        as expected.

        Initially we had constraints on the "id" field of the items in the 
        `elements` list. That is, we prevented certain identifiers from being used
        as identifying names for Observation and Feature instances.

        We ultimately decided, however, to remove that 
        "normalization" of identifiers.

        Still, we keep this test in case we ever want to re-implement
        controls on the naming conventions. In that case, ensure that
        the ensure<Bool> call below is correct for the test.
        '''
        # deserialize the payload dict
        s = self.element_set_serializer_class(data=testcase.expected_element_set_data)
        testcase.assertTrue(s.is_valid())
        element_set = s.get_instance()
        testcase.assertEqual(element_set, testcase.element_set)

        bad_data = {
            'multiple': True,
            'elements': [
                {
                    'id':'-foo', # potentially bad ID
                    'attributes': {
                        'keyA': {
                            'attribute_type': 'String',
                            'value': 'abc'
                        }
                    }
                }
            ]
        }
        s = self.element_set_serializer_class(data=bad_data)
        # if we want to impose constraints on the identifier names,
        # then uncomment the line below:
        #testcase.assertFalse(s.is_valid())
        testcase.assertTrue(s.is_valid())

    def test_conflicting_multiple_option(self, testcase):
        '''
        Tests where `multiple`=False but >1 elements are provided
        in the element list
        '''
        bad_data = {
            'multiple': False, # multiple false, but two elements below
            'elements': [
                {
                    'id':'foo',
                    'attributes': {
                        'keyA': {
                            'attribute_type': 'String',
                            'value': 'abc'
                        }
                    }
                },
                {
                    'id':'bar',
                    'attributes': {
                        'keyA': {
                            'attribute_type': 'String',
                            'value': 'abc'
                        }
                    }
                }
            ]
        }
        s = self.element_set_serializer_class(data=bad_data)
        testcase.assertFalse(s.is_valid())



class TestObservationSetSerializer(unittest.TestCase):

    def setUp(self):

        # create a couple Observations to use and a corresponding serializer
        self.el1 = Observation('sampleA', {
            'phenotype': StringAttribute('WT')
        })
        self.el1_serializer = ObservationSerializer(self.el1)

        self.el2 = Observation('sampleB', {
            'phenotype': StringAttribute('KO')
        })
        self.el2_serializer = ObservationSerializer(self.el2)


        # a duplicate of el1 above, for testing addition of duplicate elements:
        self.duplicate_element = Observation('sampleA', {})
        self.dup_element_serializer = ObservationSerializer(self.duplicate_element)

        # the correct serialized representation of an ElementSet instance
        self.expected_element_set_data = {
            'multiple': True,
            'elements': [
                self.el1_serializer.data,
                self.el2_serializer.data
            ]
        }
        # a correctly formed instance of an ObservationSet
        self.element_set = ObservationSet([self.el1, self.el2])

        # the class that will execute the tests
        self.tester_class = ElementSetSerializerTester(ObservationSetSerializer)

    def test_observationset(self):
        test_methods = [x for x in dir(self.tester_class) if x.startswith('test_')]
        for t in test_methods:
            m = getattr(self.tester_class, t)
            m(self)


class TestFeatureSetSerializer(unittest.TestCase):

    def setUp(self):

        # create a couple Features to use and a corresponding serializer
        self.el1 = Feature('geneA', {
            'oncogene': StringAttribute('WT')
        })
        self.el1_serializer = FeatureSerializer(self.el1)

        self.el2 = Feature('geneB', {
            'oncogene': StringAttribute('KO')
        })
        self.el2_serializer = FeatureSerializer(self.el2)


        # a duplicate of el1 above, for testing addition of duplicate elements:
        self.duplicate_element = Feature('geneA', {})
        self.dup_element_serializer = FeatureSerializer(self.duplicate_element)

        # the correct serialized representation of an ElementSet instance
        self.expected_element_set_data = {
            'multiple': True,
            'elements': [
                self.el1_serializer.data,
                self.el2_serializer.data
            ]
        }
        # a correctly formed instance of an FeatureSet
        self.element_set = FeatureSet([self.el1, self.el2])

        # the class that will execute the tests
        self.tester_class = ElementSetSerializerTester(FeatureSetSerializer)

    def test_featureset(self):
        test_methods = [x for x in dir(self.tester_class) if x.startswith('test_')]
        for t in test_methods:
            m = getattr(self.tester_class, t)
            m(self)
