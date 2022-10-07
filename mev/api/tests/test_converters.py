import unittest.mock as mock
import os
import uuid

from exceptions import AttributeValueError, \
    DataStructureValidationException, \
    StringIdentifierException

from data_structures.observation import Observation
from data_structures.observation_set import ObservationSet
from data_structures.feature import Feature
from data_structures.feature_set import FeatureSet

from api.models import Resource
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

from api.converters.data_resource import \
    LocalDockerSingleDataResourceConverter, \
    LocalDockerSingleVariableDataResourceConverter, \
    LocalDockerSingleDataResourceWithTypeConverter, \
    LocalDockerMultipleDataResourceConverter, \
    LocalDockerMultipleVariableDataResourceConverter, \
    LocalDockerDelimitedResourceConverter, \
    LocalDockerCsvResourceConverter, \
    LocalDockerSpaceDelimResourceConverter, \
    CromwellSingleDataResourceConverter, \
    CromwellMultipleDataResourceConverter

from api.converters.element_set import ObservationSetCsvConverter, \
    FeatureSetCsvConverter, \
    ObservationSetListConverter, \
    FeatureSetListConverter
from api.tests.base import BaseAPITestCase

class TestBasicAttributeConverter(BaseAPITestCase):

    def test_basic_attributes(self):
        s = StringConverter()
        v = s.convert_input('abc', '', '')
        self.assertEqual(v, 'abc')

        v = s.convert_input('ab c', '', '')
        self.assertEqual(v, 'ab_c')

        with self.assertRaises(AttributeValueError):
            v = s.convert_input('ab?c', '', '')

        s = UnrestrictedStringConverter()
        v = s.convert_input('abc', '', '')
        self.assertEqual(v, 'abc')
        v = s.convert_input('ab c', '', '')
        self.assertEqual(v, 'ab c')
        v = s.convert_input('ab?c', '', '')
        self.assertEqual(v, 'ab?c')

        ic = IntegerConverter()
        i = ic.convert_input( 2, '', '')
        self.assertEqual(i,2)

        with self.assertRaises(AttributeValueError):
            ic.convert_input('1', '', '')
        with self.assertRaises(AttributeValueError):
            ic.convert_input('1.2', '', '')

        with self.assertRaises(AttributeValueError):
            ic.convert_input('a', '', '')

        s = StringListConverter()
        v = s.convert_input( ['ab','c d'], '', '')
        self.assertCountEqual(['ab','c_d'], v)

        with self.assertRaises(DataStructureValidationException):
            v = s.convert_input( 2, '', '')

        with self.assertRaises(AttributeValueError):
            v = s.convert_input( ['1','2'], '', '')

        s = UnrestrictedStringListConverter()
        v = s.convert_input( ['ab','c d'], '', '')
        self.assertCountEqual(['ab','c d'], v)

        c = StringListToCsvConverter()
        v = c.convert_input( ['aaa','bbb','ccc'], '', '')
        self.assertEqual(v, 'aaa,bbb,ccc')

        c = StringListToCsvConverter()
        v = c.convert_input( ['a b','c d'], '', '')
        self.assertEqual(v, 'a_b,c_d')

        c = StringListToCsvConverter()
        with self.assertRaises(AttributeValueError):
            v = c.convert_input( ['a?b','c d'], '', '')

        c = UnrestrictedStringListToCsvConverter()
        v = c.convert_input(['aaa','bbb','ccc'], '', '')
        self.assertEqual(v, 'aaa,bbb,ccc')

        c = UnrestrictedStringListToCsvConverter()
        v = c.convert_input( ['a b','c d'], '', '')
        self.assertEqual(v, 'a b,c d')

        c = UnrestrictedStringListToCsvConverter()
        v = c.convert_input( ['a?b','c d'], '', '')
        self.assertEqual(v, 'a?b,c d')
        
        c = NormalizingListToCsvConverter()
        v = c.convert_input( ['a b', 'c  d'], '', '')
        self.assertEqual(v, 'a_b,c__d')

        c = NormalizingListToCsvConverter()
        with self.assertRaises(StringIdentifierException):
            v = c.convert_input( ['a b', 'c ? d'], '', '')

        c = NormalizingStringConverter()
        v = c.convert_input( 'a b.tsv', '', '')
        self.assertEqual(v, 'a_b.tsv')

        c = NormalizingStringConverter()
        with self.assertRaises(StringIdentifierException):
            v = c.convert_input( 'c ? d', '', '')


class TestElementSetConverter(BaseAPITestCase):

    def test_observation_set_csv_converter(self):
        obs_set = ObservationSet(
            {'elements': [
                {
                    'id': 'foo'
                },
                {
                    'id': 'bar'
                }
            ]}
        )
        d = obs_set.to_simple_dict()
        c = ObservationSetCsvConverter()  
        # order doesn't matter, so need to check both orders: 
        converted_input = c.convert_input(d, '', '') 
        self.assertTrue(
            ('foo,bar' == converted_input)
            |
            ('bar,foo' == converted_input)
        )

    def test_feature_set_csv_converter(self):
        f_set = FeatureSet(
            {'elements': [
                {
                    'id': 'foo'
                },
                {
                    'id': 'bar'
                }
            ]}
        )
        d = f_set.to_simple_dict()
        c = FeatureSetCsvConverter()  
        # order doesn't matter, so need to check both orders:      
        converted_input = c.convert_input(d, '', '') 
        self.assertTrue(
            ('foo,bar' == converted_input)
            |
            ('bar,foo' == converted_input)
        )

    def test_observation_set_list_converter(self):
        '''
        Tests that we get properly formatted JSON-compatible
        arrays (of strings in this case). Used when we need to
        supply a WDL job with a list of relevant samples as an
        array of strings, for instance.
        '''
        obs_set = ObservationSet(
            {'elements': [
                {
                    'id': 'foo'
                },
                {
                    'id': 'bar'
                }
            ]}
        )
        d = obs_set.to_simple_dict()
        c = ObservationSetListConverter()  
        # order doesn't matter, so need to check both orders: 
        converted_input = c.convert_input(d, '', '') 
        self.assertCountEqual(['foo','bar'], converted_input)

    def test_feature_set_list_converter(self):
        '''
        Tests that we get properly formatted JSON-compatible
        arrays (of strings in this case). Used when we need to
        supply a WDL job with a list of relevant samples as an
        array of strings, for instance.
        '''
        f_set = FeatureSet(
            {'elements': [
                {
                    'id': 'foo'
                },
                {
                    'id': 'bar'
                }
            ]}
        )
        d = f_set.to_simple_dict()
        c = FeatureSetListConverter()  
        # order doesn't matter, so need to check both orders: 
        converted_input = c.convert_input(d, '', '') 
        self.assertCountEqual(['foo','bar'], converted_input)

class TestDataResourceConverter(BaseAPITestCase):

    def test_single_local_converter(self):
        '''
        Tests that the converter can take a single Resource instance
        and return the local path
        '''
        user_input = str(uuid.uuid4())

        mock_path = '/some/mock/path.txt'
        mock_staging_dir = '/some/staging_dir'
        mock_convert_resource_input = mock.MagicMock()
        mock_convert_resource_input.return_value = mock_path

        c = LocalDockerSingleDataResourceConverter()
        c._convert_resource_input = mock_convert_resource_input
        x = c.convert_input( user_input, '', mock_staging_dir)
        self.assertEqual(x, mock_path)
        mock_convert_resource_input.assert_called_once_with(
            user_input, mock_staging_dir)

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
        mock_convert_resource_input = mock.MagicMock()
        mock_convert_resource_input.return_value = mock_path

        c = LocalDockerSingleDataResourceWithTypeConverter()
        c._convert_resource_input = mock_convert_resource_input

        x = c.convert_input( user_input, '', mock_staging_dir)
        delim = LocalDockerSingleDataResourceWithTypeConverter.DELIMITER
        expected_str = f'{mock_path}{delim}{rt}'
        self.assertEqual(x, expected_str)
        mock_convert_resource_input.assert_called_once_with(
            user_input, mock_staging_dir)

    def test_single_cromwell_converter(self):
        '''
        Tests that the converter can take a single Resource instance
        and return the path to a bucket-based file
        '''
        mock_input = str(uuid.uuid4())
        mock_path = '/path/to/file.txt'
        mock_staging_dir = '/some/staging_dir/'

        c = CromwellSingleDataResourceConverter()
        mock_convert_resource_input = mock.MagicMock()
        mock_convert_resource_input.return_value = mock_path
        c._convert_resource_input = mock_convert_resource_input

        x = c.convert_input( mock_input, '', mock_staging_dir)
        self.assertEqual(x,  mock_path)
        mock_convert_resource_input.assert_called_with(mock_input, mock_staging_dir)

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
        # patch a method on that class. This method is the
        # one which gets the Resource and gets the fully
        # resolved path in our storage system.
        c._convert_resource_input = mock.MagicMock()
        c._convert_resource_input.side_effect = mock_path_list
        
        expected_result = mock_path_list
        x = c.convert_input( uuid_list, '', '/some/staging_dir/')
        self.assertEqual(x, expected_result)

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

        mock_convert_resource_input = mock.MagicMock()
        mock_convert_resource_input.side_effect = mock_paths

        c = LocalDockerMultipleDataResourceConverter()
        c._convert_resource_input = mock_convert_resource_input
        x = c.convert_input( mock_inputs, '', mock_staging_dir)
        self.assertEqual(x,  mock_paths)
        mock_convert_resource_input.assert_has_calls([
            mock.call(u, mock_staging_dir) for u in mock_inputs
        ])

        c = LocalDockerCsvResourceConverter()
        mock_convert_resource_input.reset_mock()
        mock_convert_resource_input.side_effect = mock_paths
        c._convert_resource_input = mock_convert_resource_input
        x = c.convert_input( mock_inputs, '', mock_staging_dir)
        expected = ','.join(mock_paths)
        self.assertEqual(x,  expected)
        mock_convert_resource_input.assert_has_calls([
            mock.call(u, mock_staging_dir) for u in mock_inputs
        ])

        c = LocalDockerSpaceDelimResourceConverter()
        mock_convert_resource_input.reset_mock()
        mock_convert_resource_input.side_effect = mock_paths
        c._convert_resource_input = mock_convert_resource_input
        x = c.convert_input( mock_inputs, '', mock_staging_dir)
        expected = ' '.join(mock_paths)
        self.assertEqual(x,  expected)
        mock_convert_resource_input.assert_has_calls([
            mock.call(u, mock_staging_dir) for u in mock_inputs
        ])

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

        mock_convert_resource_input = mock.MagicMock()
        mock_convert_resource_input.return_value = mock_path

        c = LocalDockerMultipleDataResourceConverter()
        c._convert_resource_input = mock_convert_resource_input
        x = c.convert_input( mock_input, '', mock_staging_dir)
        self.assertEqual(x,  [mock_path])
        mock_convert_resource_input.assert_called_once_with(
            mock_input, mock_staging_dir)

        c = LocalDockerCsvResourceConverter()
        mock_convert_resource_input.reset_mock()
        c._convert_resource_input = mock_convert_resource_input
        x = c.convert_input( mock_input, '', mock_staging_dir)
        self.assertEqual(x,  mock_path)
        mock_convert_resource_input.assert_called_once_with(
            mock_input, mock_staging_dir)

        c = LocalDockerSpaceDelimResourceConverter()
        mock_convert_resource_input.reset_mock()
        c._convert_resource_input = mock_convert_resource_input
        x = c.convert_input( mock_input, '', mock_staging_dir)
        self.assertEqual(x,  mock_path)
        mock_convert_resource_input.assert_called_once_with(
            mock_input, mock_staging_dir)

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
        mock_convert_resource_input = mock.MagicMock()
        mock_convert_resource_input.return_value = mock_path
        c._convert_resource_input = mock_convert_resource_input
        mock_staging_dir = '/some/staging_dir/'
        x = c.convert_input(str(r.pk), '', mock_staging_dir)
        # response should be a LIST of paths.
        self.assertEqual(x, [mock_path])
        mock_convert_resource_input.assert_called_once_with(
            str(r.pk),
            mock_staging_dir
        )


class TestBooleanConverters(BaseAPITestCase):

    def test_basic_conversion(self):
        c = BooleanAsIntegerConverter()
        x = c.convert_input( 1, '/tmp', '')
        self.assertEqual(x, 1)

        x = c.convert_input( True, '/tmp', '')
        self.assertEqual(x, 1)

        x = c.convert_input( 'true', '/tmp', '')
        self.assertEqual(x, 1)

        with self.assertRaises(AttributeValueError):
            x = c.convert_input( '1', '/tmp', '')

        # check the false'y vals:
        x = c.convert_input( 0, '/tmp', '')
        self.assertEqual(x, 0)

        x = c.convert_input( False, '/tmp', '')
        self.assertEqual(x, 0)

        x = c.convert_input( 'false', '/tmp', '')
        self.assertEqual(x, 0)

        with self.assertRaises(AttributeValueError):
            x = c.convert_input( '0', '/tmp', '')