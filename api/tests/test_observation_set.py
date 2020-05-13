import unittest

from rest_framework.exceptions import ValidationError

from api.data_structures import Observation, \
    ObservationSet, \
    StringAttribute
from api.serializers import ObservationSerializer, ObservationSetSerializer


class TestObservationSet(unittest.TestCase):

    def setUp(self):
        # create a couple Observations to use
        self.obs1 = Observation('sampleA', {
            'phenotype': StringAttribute('WT')
        })

        self.obs2 = Observation('sampleB', {
            'phenotype': StringAttribute('KO')
        })

        # a duplicate of obs1 above:
        self.duplicate_obs = Observation('sampleA', {})

    def test_create_observation_set(self):
        obs_list = [self.obs1, self.obs2]
        obs_set = ObservationSet(obs_list, True)
        self.assertEqual(
            obs_set.observations, 
            set([self.obs1, self.obs2])
        )
        # test without setting the explicit arg for multiple:
        obs_set = ObservationSet(obs_list)
        self.assertEqual(
            obs_set.observations, 
            set([self.obs1, self.obs2])
        )

    def test_create_singleton_observation_set(self):
        obs_list = [self.obs1, self.obs2]
        with self.assertRaises(ValidationError):
            obs_set = ObservationSet(obs_list, False)

    def test_duplicate_element_rejected_on_creation(self):
        obs_list = [self.obs1, self.duplicate_obs]
        with self.assertRaises(ValidationError):
            obs_set = ObservationSet(obs_list)

    def test_raises_exception_on_duplicate_add(self):
        obs_list = [self.obs1, self.obs2]
        obs_set = ObservationSet(obs_list)
        with self.assertRaises(ValidationError):
            obs_set.add_observation(self.duplicate_obs)

    def test_observation_set_equality(self):
        obs_list1 = [self.obs1, self.obs2]
        obs_list2 = [self.duplicate_obs, self.obs2]
        obs_set1 = ObservationSet(obs_list1)  
        obs_set2 = ObservationSet(obs_list2)  
        self.assertEqual(obs_set1, obs_set2)
    
    def test_observation_set_equivalence(self):
        obs_list1 = [self.obs1, self.obs2]
        obs_list2 = [self.duplicate_obs, self.obs2]
        obs_set1 = ObservationSet(obs_list1)  
        obs_set2 = ObservationSet(obs_list2)  
        self.assertTrue(obs_set1.is_equivalent_to(obs_set2))

    def test_observation_superset(self):
        obs_list1 = [self.obs1, self.obs2]
        obs_list2 = [self.obs2]
        obs_set1 = ObservationSet(obs_list1)  
        obs_set2 = ObservationSet(obs_list2)  
        self.assertTrue(obs_set1.is_proper_superset_of(obs_set2))

    def test_observation_subset(self):
        obs_list1 = [self.obs1, self.obs2]
        obs_list2 = [self.obs2]
        obs_set1 = ObservationSet(obs_list1)  
        obs_set2 = ObservationSet(obs_list2)  
        self.assertTrue(obs_set2.is_proper_subset_of(obs_set1))

    def test_set_difference(self):
        obs_list1 = [self.obs1, self.obs2]
        obs_list2 = [self.obs2]
        obs_set1 = ObservationSet(obs_list1)  
        obs_set2 = ObservationSet(obs_list2)  
        diff_set = obs_set1.set_difference(obs_set2)
        self.assertEqual(len(diff_set), 1)
        self.assertEqual(diff_set, set([self.obs1]))

    def test_set_intersection(self):
        obs_list1 = [self.obs1, self.obs2]
        obs_list2 = [self.obs2]
        obs_set1 = ObservationSet(obs_list1)  
        obs_set2 = ObservationSet(obs_list2)  
        int_set = obs_set1.set_intersection(obs_set2)
        self.assertEqual(len(int_set), 1)
        self.assertEqual(int_set, set([self.obs2]))


class TestObservationSetSerializer(unittest.TestCase):

    def setUp(self):

        # create a couple Observations to use
        self.obs1 = Observation('sampleA', {
            'phenotype': StringAttribute('WT')
        })
        self.obs1_serializer = ObservationSerializer(self.obs1)

        self.obs2 = Observation('sampleB', {
            'phenotype': StringAttribute('KO')
        })
        self.obs2_serializer = ObservationSerializer(self.obs2)

        # a duplicate of obs1 above:
        self.duplicate_obs = Observation('sampleA', {})
        self.dup_obs_serializer = ObservationSerializer(self.duplicate_obs)

        self.expected_obs_set_data = {
            'multiple': True,
            'observations': [
                self.obs1_serializer.data,
                self.obs2_serializer.data
            ]
        }
        self.obs_set = ObservationSet([self.obs1, self.obs2])


    def test_serialization(self):

        serialzed_obs_set = ObservationSetSerializer(self.obs_set)

        # to test equality, we have to convert from a list of OrderedDict to 
        # a list of dict:
        new_list = []
        for o in serialzed_obs_set.data['observations']:
            new_list.append(dict(o))
        new_list = sorted(new_list, key=lambda x:x['id'])

        # assert equality of the Observation lists
        self.assertListEqual(
            new_list, 
            self.expected_obs_set_data['observations'])
        self.assertEqual(
            self.expected_obs_set_data['multiple'],
            serialzed_obs_set.data['multiple']
        )

    def test_deserialization(self):
        s = ObservationSetSerializer(data=self.expected_obs_set_data)
        self.assertTrue(s.is_valid())
        obs_set = s.get_instance()
        self.assertEqual(obs_set, self.obs_set)

        bad_data = {
            'multiple': True,
            'observations': [
                {
                    'id':'-foo', # bad ID
                    'attributes': {
                        'keyA': {
                            'attribute_type': 'String',
                            'value': 'abc'
                        }
                    }
                }
            ]
        }
        s = ObservationSetSerializer(data=bad_data)
        self.assertFalse(s.is_valid())

    def test_foo(self):
        bad_data = {
            'multiple': False, # multiple false, but two observations below
            'observations': [
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
        s = ObservationSetSerializer(data=bad_data)
        self.assertFalse(s.is_valid())
