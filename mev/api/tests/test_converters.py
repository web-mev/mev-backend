import unittest
import unittest.mock as mock
from django.core.exceptions import ImproperlyConfigured
from api.models import Resource
from api.data_structures import Observation, ObservationSet, Feature, FeatureSet
from api.converters.data_resource import LocalDataResourceConverter, \
    LocalDockerCsvResourceConverter, \
    LocalDockerSpaceDelimResourceConverter, \
    LocalDockerSingleDataResourceConverter
from api.converters.element_set import ObservationSetCsvConverter, FeatureSetCsvConverter
from api.tests.base import BaseAPITestCase

class TestElementSetConverter(BaseAPITestCase):

    def test_observation_set_csv_converter(self):
        obs1 = Observation('foo')
        obs2 = Observation('bar')
        obs_set = ObservationSet([obs1, obs2])
        d = obs_set.to_dict()
        c = ObservationSetCsvConverter()  
        # order doesn't matter, so need to check both orders:      
        self.assertTrue(
            ('foo,bar'== c.convert(d))
            |
            ('bar,foo'== c.convert(d))
        )

    def test_feature_set_csv_converter(self):
        f1 = Feature('foo')
        f2 = Feature('bar')
        f_set = FeatureSet([f1, f2])
        d = f_set.to_dict()
        c = FeatureSetCsvConverter()  
        # order doesn't matter, so need to check both orders:      
        self.assertTrue(
            ('foo,bar'== c.convert(d))
            |
            ('bar,foo'== c.convert(d))
        )

class TestDataResourceConverter(BaseAPITestCase):

    @mock.patch('api.converters.data_resource.settings')
    def test_single_local_converter(self, mock_settings):
        '''
        Tests that the converter can take a single Resource instance
        and return the local path
        '''
        p = '/foo/bar.txt'
        mock_settings.RESOURCE_STORAGE_BACKEND.get_local_resource_path.return_value = p

        # the validators will check the validity of the user inputs prior to 
        # calling the converter. Thus, we can use basically any Resource to test
        all_resources = Resource.objects.all()
        r = all_resources[0]

        user_input = str(r.pk)
        c = LocalDockerSingleDataResourceConverter()
        x = c.convert(user_input)
        self.assertEqual(x, p)

    @mock.patch('api.converters.data_resource.settings')
    def test_csv_local_converter_case1(self, mock_settings):
        '''
        Tests that the converter can take a list of Resource instances
        and return a properly formatted comma-delim list 
        '''
        p = ['/foo/bar1.txt', '/foo/bar2.txt', '/foo/bar3.txt']
        mock_settings.RESOURCE_STORAGE_BACKEND.get_local_resource_path.side_effect = p

        # the validators will check the validity of the user inputs prior to 
        # calling the converter. Thus, we can use basically any Resource to test
        all_resources = Resource.objects.all()
        if len(all_resources) < 3:
            raise ImproperlyConfigured('Need a minimum of 3 Resources to run this test.')

        # test for multiple
        v = [str(all_resources[i].pk) for i in range(1,4)] 

        user_input = v
        c = LocalDockerCsvResourceConverter()
        x = c.convert(user_input)
        self.assertEqual(x, ','.join(p))



    @mock.patch('api.converters.data_resource.settings')
    def test_csv_local_converter_case2(self, mock_settings):
        '''
        Tests that the CSV converter can take a single Resource instance
        and return a properly formatted string 
        '''
        p = '/foo/bar1.txt'
        mock_settings.RESOURCE_STORAGE_BACKEND.get_local_resource_path.return_value = p

        # the validators will check the validity of the user inputs prior to 
        # calling the converter. Thus, we can use basically any Resource to test
        all_resources = Resource.objects.all()
        v = str(all_resources[0].pk)
        user_input = v
        c = LocalDockerCsvResourceConverter()
        x = c.convert(user_input)
        self.assertEqual(x, p)

    @mock.patch('api.converters.data_resource.settings')
    def test_space_delim_local_converter_case1(self, mock_settings):
        '''
        Tests that the converter can take a list of Resource instances
        and return a properly formatted space-delimited list.
        '''
        p = ['/foo/bar1.txt', '/foo/bar2.txt', '/foo/bar3.txt']
        mock_settings.RESOURCE_STORAGE_BACKEND.get_local_resource_path.side_effect = p

        # the validators will check the validity of the user inputs prior to 
        # calling the converter. Thus, we can use basically any Resource to test
        all_resources = Resource.objects.all()
        if len(all_resources) < 3:
            raise ImproperlyConfigured('Need a minimum of 3 Resources to run this test.')
        v = [str(all_resources[i].pk) for i in range(1,4)] 

        user_input = v
        c = LocalDockerSpaceDelimResourceConverter()
        x = c.convert(user_input)
        self.assertEqual(x, ' '.join(p))

    @mock.patch('api.converters.data_resource.settings')
    def test_space_delim_local_converter_case2(self, mock_settings):
        '''
        Tests that the converter can take a single Resource instance
        and return a properly formatted space-delimited list.
        '''
        p = '/foo/bar1.txt'
        mock_settings.RESOURCE_STORAGE_BACKEND.get_local_resource_path.return_value = p

        # the validators will check the validity of the user inputs prior to 
        # calling the converter. Thus, we can use basically any Resource to test
        all_resources = Resource.objects.all()
        v = str(all_resources[0].pk)

        user_input = v
        c = LocalDockerSpaceDelimResourceConverter()
        x = c.convert(user_input)
        self.assertEqual(x, p)