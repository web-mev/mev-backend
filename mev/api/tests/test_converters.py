import unittest
import unittest.mock as mock
import os
import uuid
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
    BooleanAsIntegerConverter, \
    NormalizingListToCsvConverter, \
    NormalizingStringConverter
from api.converters.data_resource import LocalDataResourceConverter, \
    LocalDockerCsvResourceConverter, \
    LocalDockerSpaceDelimResourceConverter, \
    LocalDockerSingleDataResourceConverter, \
    LocalDockerSingleDataResourceWithTypeConverter, \
    LocalDockerMultipleDataResourceConverter, \
    CromwellSingleDataResourceConverter, \
    CromwellMultipleDataResourceConverter, \
    CromwellCsvResourceConverter, \
    CromwellSpaceDelimResourceConverter
from api.converters.mappers import SimpleFileBasedMapConverter
from api.converters.element_set import ObservationSetCsvConverter, \
    FeatureSetCsvConverter, \
    ObservationSetListConverter, \
    FeatureSetListConverter
from api.tests.base import BaseAPITestCase

class TestBasicAttributeConverter(BaseAPITestCase):

    def test_basic_attributes(self):
        s = StringConverter()
        v = s.convert('foo','abc', '', '')
        self.assertDictEqual(v, {'foo':'abc'})

        v = s.convert('foo','ab c', '', '')
        self.assertDictEqual(v, {'foo':'ab_c'})

        with self.assertRaises(AttributeValueError):
            v = s.convert('foo','ab?c', '', '')

        s = UnrestrictedStringConverter()
        v = s.convert('foo','abc', '', '')
        self.assertDictEqual(v, {'foo':'abc'})
        v = s.convert('foo','ab c', '', '')
        self.assertDictEqual(v, {'foo':'ab c'})
        v = s.convert('foo','ab?c', '', '')
        self.assertDictEqual(v, {'foo':'ab?c'})

        ic = IntegerConverter()
        i = ic.convert('foo', 2, '', '')
        self.assertDictEqual(i,{'foo':2})

        with self.assertRaises(AttributeValueError):
            ic.convert('foo','1', '', '')
        with self.assertRaises(AttributeValueError):
            ic.convert('foo','1.2', '', '')

        with self.assertRaises(AttributeValueError):
            ic.convert('foo','a', '', '')

        s = StringListConverter()
        v = s.convert('foo', ['ab','c d'], '', '')
        self.assertCountEqual(v.keys(), ['foo',])
        self.assertCountEqual(['ab','c_d'], v['foo'])

        with self.assertRaises(AttributeValueError):
            v = s.convert('foo', 2, '', '')

        with self.assertRaises(AttributeValueError):
            v = s.convert('foo', ['1','2'], '', '')

        s = UnrestrictedStringListConverter()
        v = s.convert('foo', ['ab','c d'], '', '')
        self.assertCountEqual(v.keys(), ['foo',])
        self.assertCountEqual(['ab','c d'], v['foo'])

        c = StringListToCsvConverter()
        v = c.convert('foo', ['aaa','bbb','ccc'], '', '')
        self.assertDictEqual(v, {'foo':'aaa,bbb,ccc'})

        c = StringListToCsvConverter()
        v = c.convert('foo', ['a b','c d'], '', '')
        self.assertDictEqual(v, {'foo':'a_b,c_d'})

        c = StringListToCsvConverter()
        with self.assertRaises(AttributeValueError):
            v = c.convert('foo', ['a?b','c d'], '', '')

        c = UnrestrictedStringListToCsvConverter()
        v = c.convert('foo',['aaa','bbb','ccc'], '', '')
        self.assertDictEqual(v, {'foo':'aaa,bbb,ccc'})

        c = UnrestrictedStringListToCsvConverter()
        v = c.convert('foo', ['a b','c d'], '', '')
        self.assertDictEqual(v, {'foo':'a b,c d'})

        c = UnrestrictedStringListToCsvConverter()
        v = c.convert('foo', ['a?b','c d'], '', '')
        self.assertDictEqual(v, {'foo':'a?b,c d'})
        
        c = NormalizingListToCsvConverter()
        v = c.convert('foo', ['a b', 'c  d'], '', '')
        self.assertDictEqual(v, {'foo':'a_b,c__d'})

        c = NormalizingListToCsvConverter()
        with self.assertRaises(AttributeValueError):
            v = c.convert('foo', ['a b', 'c ? d'], '', '')

        c = NormalizingStringConverter()
        v = c.convert('foo', 'a b.tsv', '', '')
        self.assertDictEqual(v, {'foo':'a_b.tsv'})

        c = NormalizingStringConverter()
        with self.assertRaises(AttributeValueError):
            v = c.convert('foo', 'c ? d', '', '')


class TestElementSetConverter(BaseAPITestCase):

    def test_observation_set_csv_converter(self):
        obs1 = Observation('foo')
        obs2 = Observation('bar')
        obs_set = ObservationSet([obs1, obs2])
        d = obs_set.to_dict()
        c = ObservationSetCsvConverter()  
        # order doesn't matter, so need to check both orders: 
        converted_input = c.convert('xyz', d, '', '') 
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
        converted_input = c.convert('xyz', d, '', '') 
        self.assertTrue(
            ({'xyz': 'foo,bar'} == converted_input)
            |
            ({'xyz':'bar,foo'} == converted_input)
        )

    def test_observation_set_list_converter(self):
        '''
        Tests that we get properly formatted JSON-compatible
        arrays (of strings in this case). Used when we need to
        supply a WDL job with a list of relevant samples as an
        array of strings, for instance.
        '''
        obs1 = Observation('foo')
        obs2 = Observation('bar')
        obs_set = ObservationSet([obs1, obs2])
        d = obs_set.to_dict()
        c = ObservationSetListConverter()  
        # order doesn't matter, so need to check both orders: 
        converted_input = c.convert('xyz', d, '', '') 
        self.assertTrue(
            ({'xyz': ['foo','bar']} == converted_input)
            |
            ({'xyz':['bar','foo']} == converted_input)
        )

    def test_feature_set_list_converter(self):
        '''
        Tests that we get properly formatted JSON-compatible
        arrays (of strings in this case). Used when we need to
        supply a WDL job with a list of relevant samples as an
        array of strings, for instance.
        '''
        obs1 = Feature('foo')
        obs2 = Feature('bar')
        obs_set = FeatureSet([obs1, obs2])
        d = obs_set.to_dict()
        c = FeatureSetListConverter()  
        # order doesn't matter, so need to check both orders: 
        converted_input = c.convert('xyz', d, '', '') 
        self.assertTrue(
            ({'xyz': ['foo','bar']} == converted_input)
            |
            ({'xyz':['bar','foo']} == converted_input)
        )

class TestDataResourceConverter(BaseAPITestCase):

    def test_single_local_converter(self):
        '''
        Tests that the converter can take a single Resource instance
        and return the local path
        '''
        user_input = str(uuid.uuid4())

        mock_path = '/some/mock/path.txt'
        mock_staging_dir = '/some/staging_dir'
        c = LocalDockerSingleDataResourceConverter()
        mock_copy = mock.MagicMock()
        mock_copy.return_value = mock_path
        c._copy_resource_to_staging = mock_copy
        x = c.convert('foo', user_input, '', mock_staging_dir)
        mock_copy.assert_called_with(user_input, mock_staging_dir)
        self.assertDictEqual(x, {'foo':  mock_path})

    def test_single_local_with_rt_converter(self):
        '''
        Tests that the converter can take a single Resource instance
        and return the local path AND resource type as a special delimited string
        '''
        # the validators will check the validity of the user inputs prior to 
        # calling the converter. Thus, we can use basically any Resource to test
        all_resources = Resource.objects.all()
        r = all_resources[0]
        rt = r.resource_type

        user_input = str(r.pk)
        mock_path = '/path/to/file.txt'
        mock_staging_dir = '/path/to/dir'
        c = LocalDockerSingleDataResourceWithTypeConverter()
        mock_get_resource = mock.MagicMock()
        mock_get_resource.return_value = r
        mock_copy = mock.MagicMock()
        mock_copy.return_value = mock_path
        c.get_resource = mock_get_resource
        c._copy_resource_to_staging = mock_copy

        x = c.convert('foo', user_input, '', mock_staging_dir)
        mock_copy.assert_called_with(str(r.pk), mock_staging_dir)
        expected_str = '{p}{d}{rt}'.format(
            p = mock_path,
            d = LocalDockerSingleDataResourceWithTypeConverter.DELIMITER,
            rt = rt
        )
        self.assertDictEqual(x, {'foo': expected_str})

    def test_single_cromwell_converter(self):
        '''
        Tests that the converter can take a single Resource instance
        and return the path to a bucket-based file
        '''
        mock_input = str(uuid.uuid4())
        mock_path = '/path/to/file.txt'
        mock_staging_dir = '/some/staging_dir/'

        c = CromwellSingleDataResourceConverter()
        mock_convert_single_resource = mock.MagicMock()
        mock_convert_single_resource.return_value = mock_path
        c._convert_single_resource = mock_convert_single_resource

        x = c.convert('foo', mock_input, '', mock_staging_dir)
        self.assertDictEqual(x, {'foo': mock_path})
        mock_convert_single_resource.assert_called_with(mock_input, mock_staging_dir)

    def test_cromwell_converters_case1(self):
        '''
        Tests that the CromwellMultipleDataResourceConverter
        converter can take a list of Resource instances
        and return a properly formatted response. The response
        depends on the actual implementing class.

        Here we test with multiple input resource UUIDs
        '''
        uuid_list = [str(uuid.uuid4()) for i in range(3)]

        c = CromwellMultipleDataResourceConverter()
        mock_path_list = [
            '/path/to/a.txt',
            '/path/to/b.txt',
            '/path/to/c.txt',
        ]
        # patch a method on that class:
        c._convert_single_resource = mock.MagicMock()
        c._convert_single_resource.side_effect = mock_path_list
        
        expected_result = mock_path_list
        x = c.convert('foo', uuid_list, '', '/some/staging_dir/')
        self.assertDictEqual(x, {'foo':expected_result})

        # instantiate and patch a method on the CSV class:
        c = CromwellCsvResourceConverter()
        c._convert_single_resource = mock.MagicMock()
        c._convert_single_resource.side_effect = mock_path_list
        expected_result = ','.join(mock_path_list)
        x = c.convert('foo', uuid_list, '', '/some/staging_dir/')
        self.assertDictEqual(x, {'foo':expected_result})

        c = CromwellSpaceDelimResourceConverter()
        c._convert_single_resource = mock.MagicMock()
        c._convert_single_resource.side_effect = mock_path_list
        expected_result = ' '.join(mock_path_list)
        x = c.convert('foo', uuid_list, '', '/some/staging_dir/')
        self.assertDictEqual(x, {'foo':expected_result})

    def test_multiple_resource_local_converter_case1(self):
        '''
        Tests that the converter can take a list of Resource instance UUIDs
        and return a properly formatted response.

        This covers the LocalDockerMultipleDataResourceConverter
        and derived classes
        '''
        mock_paths = ['/foo/bar1.txt', '/foo/bar2.txt', '/foo/bar3.txt']
        mock_staging_dir = '/some/staging_dir'
        mock_inputs = [str(uuid.uuid4()) for _ in range(len(mock_paths))]

        mock_get_path_list = mock.MagicMock()
        mock_get_path_list.return_value = mock_paths
        c = LocalDockerMultipleDataResourceConverter()
        c._get_path_list = mock_get_path_list
        x = c.convert('foo', mock_inputs, '', mock_staging_dir)
        self.assertDictEqual(x, {'foo': mock_paths})

        c = LocalDockerCsvResourceConverter()
        c._get_path_list = mock_get_path_list
        x = c.convert('foo', mock_inputs, '', mock_staging_dir)
        expected = ','.join(mock_paths)
        self.assertDictEqual(x, {'foo': expected})

        c = LocalDockerSpaceDelimResourceConverter()
        c._get_path_list = mock_get_path_list
        x = c.convert('foo', mock_inputs, '', mock_staging_dir)
        expected = ' '.join(mock_paths)
        self.assertDictEqual(x, {'foo': expected})
        
        mock_get_path_list.assert_called_with(mock_inputs, mock_staging_dir)

    def test_multiple_resource_local_converter_case2(self):
        '''
        Tests that the converter can take a "list" of a single 
        Resource instance UUID
        and return a properly formatted response.

        This covers the LocalDockerMultipleDataResourceConverter
        and derived classes
        '''
        mock_path = '/foo/bar1.txt'
        mock_staging_dir = '/some/staging_dir'
        mock_input = str(uuid.uuid4())

        mock_get_path_list = mock.MagicMock()
        mock_get_path_list.return_value = [mock_path]
        c = LocalDockerMultipleDataResourceConverter()
        c._get_path_list = mock_get_path_list
        x = c.convert('foo', mock_input, '', mock_staging_dir)
        self.assertDictEqual(x, {'foo': [mock_path]})

        c = LocalDockerCsvResourceConverter()
        c._get_path_list = mock_get_path_list
        x = c.convert('foo', mock_input, '', mock_staging_dir)
        self.assertDictEqual(x, {'foo': mock_path})

        c = LocalDockerSpaceDelimResourceConverter()
        c._get_path_list = mock_get_path_list
        x = c.convert('foo', mock_input, '', mock_staging_dir)
        self.assertDictEqual(x, {'foo': mock_path})

        mock_get_path_list.assert_called_with(mock_input, mock_staging_dir)

    @mock.patch('api.converters.data_resource.get_resource_by_pk')
    def test_cromwell_converters_case2(self, mock_get_resource_by_pk):
        '''
        Tests that the multiple DataResource converters 
        can take a list of Resource instances
        and return a properly formatted response (which depends
        on the converter class)

        Here, we pass only a single resource UUID. 
        For example, we may have a WDL workflow which can accept >=1 
        inputs as an array. Here we test that passing a single input
        results in a list of paths of length 1.
        '''

        all_resources = Resource.objects.all()
        r = all_resources[0]

        mock_path = '/path/to/a.txt'
        # instantiate and patch a method on that class:
        c = CromwellMultipleDataResourceConverter()
        c._convert_single_resource = mock.MagicMock()
        c._convert_single_resource.return_value = mock_path

        x = c.convert('foo', str(r.pk), '', '/some/staging_dir/')
        # response should be a LIST of paths.
        self.assertDictEqual(x, {'foo':[mock_path]})

        c = CromwellCsvResourceConverter()
        c._convert_single_resource = mock.MagicMock()
        c._convert_single_resource.return_value = mock_path

        x = c.convert('foo', str(r.pk), '', '/some/staging_dir/')
        # response should be a csv-string of paths, which is simply
        # the path in this case.
        self.assertDictEqual(x, {'foo':mock_path})


class TestMapConverters(BaseAPITestCase):

    def test_missing_map_file(self):
        c = SimpleFileBasedMapConverter()
        with self.assertRaises(InputMappingException):
            c.convert('foo', 'abc', '', '/some/staging_dir/')

    def test_bad_json_data(self):
        # missing quotes on "abc"
        bad_json_str = '{"foo": abc}'
        tmp_path = os.path.join('/tmp', SimpleFileBasedMapConverter.MAPPING_FILE)
        with open(tmp_path, 'w') as fout:
            fout.write(bad_json_str)
        
        c = SimpleFileBasedMapConverter()
        with self.assertRaises(InputMappingException):
            c.convert('mykey', 'foo', '/tmp', '/some/staging_dir/')
        os.remove(tmp_path)


    def test_bad_key(self):
        # map has key of foo. below we request a key of 'bar'
        json_str = '{"foo": {"keyA":"A", "keyB":"B"}}'
        tmp_path = os.path.join('/tmp', SimpleFileBasedMapConverter.MAPPING_FILE)
        with open(tmp_path, 'w') as fout:
            fout.write(json_str)
        
        c = SimpleFileBasedMapConverter()
        with self.assertRaises(InputMappingException):
            c.convert('mykey', 'bar', '/tmp', '/some/staging_dir/')
        os.remove(tmp_path)

    def test_gets_expected_map(self):
        json_str = '{"foo": {"keyA":"A", "keyB":"B"}}'
        tmp_path = os.path.join('/tmp', SimpleFileBasedMapConverter.MAPPING_FILE)
        with open(tmp_path, 'w') as fout:
            fout.write(json_str)
        
        c = SimpleFileBasedMapConverter()
        r = c.convert('mykey', 'foo', '/tmp', '/some/staging_dir/')
        self.assertDictEqual(r, {"keyA":"A", "keyB":"B"})
        os.remove(tmp_path)

class TestBooleanConverters(BaseAPITestCase):

    def test_basic_conversion(self):
        c = BooleanAsIntegerConverter()
        x = c.convert('foo', 1, '/tmp', '')
        self.assertDictEqual(x, {"foo": 1})

        x = c.convert('foo', True, '/tmp', '')
        self.assertDictEqual(x, {"foo": 1})

        x = c.convert('foo', 'true', '/tmp', '')
        self.assertDictEqual(x, {"foo": 1})

        with self.assertRaises(AttributeValueError):
            x = c.convert('foo', '1', '/tmp', '')

        # check the false'y vals:
        x = c.convert('foo', 0, '/tmp', '')
        self.assertDictEqual(x, {"foo": 0})

        x = c.convert('foo', False, '/tmp', '')
        self.assertDictEqual(x, {"foo": 0})

        x = c.convert('foo', 'false', '/tmp', '')
        self.assertDictEqual(x, {"foo": 0})

        with self.assertRaises(AttributeValueError):
            x = c.convert('foo', '0', '/tmp', '')