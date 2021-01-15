import unittest
import unittest.mock as mock
import os
from django.core.exceptions import ImproperlyConfigured

from api.models import Resource
from api.exceptions import AttributeValueError, InputMappingException
from api.data_structures import Observation, ObservationSet, Feature, FeatureSet
from api.converters.basic_attributes import StringConverter, \
    IntegerConverter, \
    StringListConverter, \
    UnrestrictedStringConverter, \
    UnrestrictedStringListConverter, \
    StringListToCsvConverter, \
    UnrestrictedStringListToCsvConverter, \
    BooleanAsIntegerConverter
from api.converters.data_resource import LocalDataResourceConverter, \
    LocalDockerCsvResourceConverter, \
    LocalDockerSpaceDelimResourceConverter, \
    LocalDockerSingleDataResourceConverter
from api.converters.mappers import SimpleFileBasedMapConverter
from api.converters.element_set import ObservationSetCsvConverter, FeatureSetCsvConverter
from api.tests.base import BaseAPITestCase

class TestBasicAttributeConverter(BaseAPITestCase):

    def test_basic_attributes(self):
        s = StringConverter()
        v = s.convert('foo','abc', '')
        self.assertDictEqual(v, {'foo':'abc'})

        v = s.convert('foo','ab c', '')
        self.assertDictEqual(v, {'foo':'ab_c'})

        with self.assertRaises(AttributeValueError):
            v = s.convert('foo','ab?c', '')

        s = UnrestrictedStringConverter()
        v = s.convert('foo','abc', '')
        self.assertDictEqual(v, {'foo':'abc'})
        v = s.convert('foo','ab c', '')
        self.assertDictEqual(v, {'foo':'ab c'})
        v = s.convert('foo','ab?c', '')
        self.assertDictEqual(v, {'foo':'ab?c'})

        ic = IntegerConverter()
        i = ic.convert('foo', 2, '')
        self.assertDictEqual(i,{'foo':2})

        with self.assertRaises(AttributeValueError):
            ic.convert('foo','1', '')
        with self.assertRaises(AttributeValueError):
            ic.convert('foo','1.2', '')

        with self.assertRaises(AttributeValueError):
            ic.convert('foo','a', '')

        s = StringListConverter()
        v = s.convert('foo', ['ab','c d'], '')
        self.assertCountEqual(v.keys(), ['foo',])
        self.assertCountEqual(['ab','c_d'], v['foo'])

        with self.assertRaises(AttributeValueError):
            v = s.convert('foo', 2, '')

        with self.assertRaises(AttributeValueError):
            v = s.convert('foo', ['1','2'], '')

        s = UnrestrictedStringListConverter()
        v = s.convert('foo', ['ab','c d'], '')
        self.assertCountEqual(v.keys(), ['foo',])
        self.assertCountEqual(['ab','c d'], v['foo'])

        c = StringListToCsvConverter()
        v = c.convert('foo', ['aaa','bbb','ccc'], '')
        self.assertDictEqual(v, {'foo':'aaa,bbb,ccc'})

        c = StringListToCsvConverter()
        v = c.convert('foo', ['a b','c d'], '')
        self.assertDictEqual(v, {'foo':'a_b,c_d'})

        c = StringListToCsvConverter()
        with self.assertRaises(AttributeValueError):
            v = c.convert('foo', ['a?b','c d'], '')

        c = UnrestrictedStringListToCsvConverter()
        v = c.convert('foo',['aaa','bbb','ccc'], '')
        self.assertDictEqual(v, {'foo':'aaa,bbb,ccc'})

        c = UnrestrictedStringListToCsvConverter()
        v = c.convert('foo', ['a b','c d'], '')
        self.assertDictEqual(v, {'foo':'a b,c d'})

        c = UnrestrictedStringListToCsvConverter()
        v = c.convert('foo', ['a?b','c d'], '')
        self.assertDictEqual(v, {'foo':'a?b,c d'})
        
class TestElementSetConverter(BaseAPITestCase):

    def test_observation_set_csv_converter(self):
        obs1 = Observation('foo')
        obs2 = Observation('bar')
        obs_set = ObservationSet([obs1, obs2])
        d = obs_set.to_dict()
        c = ObservationSetCsvConverter()  
        # order doesn't matter, so need to check both orders: 
        converted_input = c.convert('xyz', d, '') 
        self.assertTrue(
            ({'xyz': 'foo,bar'} == converted_input)
            |
            ({'xyz':'bar,foo'} == converted_input)
        )

    def test_feature_set_csv_converter(self):
        f1 = Feature('foo')
        f2 = Feature('bar')
        f_set = FeatureSet([f1, f2])
        d = f_set.to_dict()
        c = FeatureSetCsvConverter()  
        # order doesn't matter, so need to check both orders:      
        converted_input = c.convert('xyz', d, '') 
        self.assertTrue(
            ({'xyz': 'foo,bar'} == converted_input)
            |
            ({'xyz':'bar,foo'} == converted_input)
        )

class TestDataResourceConverter(BaseAPITestCase):

    @mock.patch('api.converters.data_resource.get_storage_backend')
    def test_single_local_converter(self, mock_get_storage_backend):
        '''
        Tests that the converter can take a single Resource instance
        and return the local path
        '''
        p = '/foo/bar.txt'
        mock_storage_backend = mock.MagicMock()
        mock_storage_backend.get_local_resource_path.return_value = p
        mock_get_storage_backend.return_value = mock_storage_backend

        # the validators will check the validity of the user inputs prior to 
        # calling the converter. Thus, we can use basically any Resource to test
        all_resources = Resource.objects.all()
        r = all_resources[0]

        user_input = str(r.pk)
        c = LocalDockerSingleDataResourceConverter()
        x = c.convert('foo', user_input, '')
        self.assertDictEqual(x, {'foo': p})

    @mock.patch('api.converters.data_resource.get_storage_backend')
    def test_csv_local_converter_case1(self, mock_get_storage_backend):
        '''
        Tests that the converter can take a list of Resource instances
        and return a properly formatted comma-delim list 
        '''
        p = ['/foo/bar1.txt', '/foo/bar2.txt', '/foo/bar3.txt']
        mock_storage_backend = mock.MagicMock()
        mock_storage_backend.get_local_resource_path.side_effect = p
        mock_get_storage_backend.return_value = mock_storage_backend

        # the validators will check the validity of the user inputs prior to 
        # calling the converter. Thus, we can use basically any Resource to test
        all_resources = Resource.objects.all()
        if len(all_resources) < 3:
            raise ImproperlyConfigured('Need a minimum of 3 Resources to run this test.')

        # test for multiple
        v = [str(all_resources[i].pk) for i in range(1,4)] 

        user_input = v
        c = LocalDockerCsvResourceConverter()
        x = c.convert('foo', user_input, '')
        csv = ','.join(p)
        self.assertDictEqual(x, {'foo':csv})



    @mock.patch('api.converters.data_resource.get_storage_backend')
    def test_csv_local_converter_case2(self, mock_get_storage_backend):
        '''
        Tests that the CSV converter can take a single Resource instance
        and return a properly formatted string 
        '''
        p = '/foo/bar1.txt'
        mock_storage_backend = mock.MagicMock()
        mock_storage_backend.get_local_resource_path.return_value = p
        mock_get_storage_backend.return_value = mock_storage_backend

        # the validators will check the validity of the user inputs prior to 
        # calling the converter. Thus, we can use basically any Resource to test
        all_resources = Resource.objects.all()
        v = str(all_resources[0].pk)
        user_input = v
        c = LocalDockerCsvResourceConverter()
        x = c.convert('foo', user_input, '')
        self.assertDictEqual(x, {'foo': p})

    @mock.patch('api.converters.data_resource.get_storage_backend')
    def test_space_delim_local_converter_case1(self, mock_get_storage_backend):
        '''
        Tests that the converter can take a list of Resource instances
        and return a properly formatted space-delimited list.
        '''
        p = ['/foo/bar1.txt', '/foo/bar2.txt', '/foo/bar3.txt']
        mock_storage_backend = mock.MagicMock()
        mock_storage_backend.get_local_resource_path.side_effect = p
        mock_get_storage_backend.return_value = mock_storage_backend

        # the validators will check the validity of the user inputs prior to 
        # calling the converter. Thus, we can use basically any Resource to test
        all_resources = Resource.objects.all()
        if len(all_resources) < 3:
            raise ImproperlyConfigured('Need a minimum of 3 Resources to run this test.')
        v = [str(all_resources[i].pk) for i in range(1,4)] 

        user_input = v
        c = LocalDockerSpaceDelimResourceConverter()
        x = c.convert('foo', user_input, '')
        delim_string = ' '.join(p)
        self.assertDictEqual(x, {'foo': delim_string})

    @mock.patch('api.converters.data_resource.get_storage_backend')
    def test_space_delim_local_converter_case2(self, mock_get_storage_backend):
        '''
        Tests that the converter can take a single Resource instance
        and return a properly formatted space-delimited list.
        '''
        p = '/foo/bar1.txt'
        mock_storage_backend = mock.MagicMock()
        mock_storage_backend.get_local_resource_path.return_value = p
        mock_get_storage_backend.return_value = mock_storage_backend

        # the validators will check the validity of the user inputs prior to 
        # calling the converter. Thus, we can use basically any Resource to test
        all_resources = Resource.objects.all()
        v = str(all_resources[0].pk)

        user_input = v
        c = LocalDockerSpaceDelimResourceConverter()
        x = c.convert('foo', user_input, '')
        self.assertDictEqual(x, {'foo':p})


class TestMapConverters(BaseAPITestCase):

    def test_missing_map_file(self):
        c = SimpleFileBasedMapConverter()
        with self.assertRaises(InputMappingException):
            c.convert('foo', 'abc', '')

    def test_bad_json_data(self):
        # missing quotes on "abc"
        bad_json_str = '{"foo": abc}'
        tmp_path = os.path.join('/tmp', SimpleFileBasedMapConverter.MAPPING_FILE)
        with open(tmp_path, 'w') as fout:
            fout.write(bad_json_str)
        
        c = SimpleFileBasedMapConverter()
        with self.assertRaises(InputMappingException):
            c.convert('mykey', 'foo', '/tmp')
        os.remove(tmp_path)


    def test_bad_key(self):
        # map has key of foo. below we request a key of 'bar'
        json_str = '{"foo": {"keyA":"A", "keyB":"B"}}'
        tmp_path = os.path.join('/tmp', SimpleFileBasedMapConverter.MAPPING_FILE)
        with open(tmp_path, 'w') as fout:
            fout.write(json_str)
        
        c = SimpleFileBasedMapConverter()
        with self.assertRaises(InputMappingException):
            c.convert('mykey', 'bar', '/tmp')
        os.remove(tmp_path)

    def test_gets_expected_map(self):
        json_str = '{"foo": {"keyA":"A", "keyB":"B"}}'
        tmp_path = os.path.join('/tmp', SimpleFileBasedMapConverter.MAPPING_FILE)
        with open(tmp_path, 'w') as fout:
            fout.write(json_str)
        
        c = SimpleFileBasedMapConverter()
        r = c.convert('mykey', 'foo', '/tmp')
        self.assertDictEqual(r, {"keyA":"A", "keyB":"B"})
        os.remove(tmp_path)

class TestBooleanConverters(BaseAPITestCase):

    def test_basic_conversion(self):
        c = BooleanAsIntegerConverter()
        x = c.convert('foo', 1, '/tmp')
        self.assertDictEqual(x, {"foo": 1})

        x = c.convert('foo', True, '/tmp')
        self.assertDictEqual(x, {"foo": 1})

        x = c.convert('foo', 'true', '/tmp')
        self.assertDictEqual(x, {"foo": 1})

        with self.assertRaises(AttributeValueError):
            x = c.convert('foo', '1', '/tmp')

        # check the false'y vals:
        x = c.convert('foo', 0, '/tmp')
        self.assertDictEqual(x, {"foo": 0})

        x = c.convert('foo', False, '/tmp')
        self.assertDictEqual(x, {"foo": 0})

        x = c.convert('foo', 'false', '/tmp')
        self.assertDictEqual(x, {"foo": 0})

        with self.assertRaises(AttributeValueError):
            x = c.convert('foo', '0', '/tmp')