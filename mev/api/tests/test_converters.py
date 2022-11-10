import json
import unittest.mock as mock
import uuid

from exceptions import AttributeValueError, \
    DataStructureValidationException, \
    StringIdentifierException, \
    StorageException, \
    OutputConversionException

from data_structures.observation_set import ObservationSet
from data_structures.feature_set import FeatureSet
from data_structures.operation_output import OperationOutput

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
    LocalDockerCsvResourceConverter, \
    LocalDockerSpaceDelimResourceConverter, \
    CromwellSingleDataResourceConverter, \
    CromwellMultipleDataResourceConverter

from api.converters.element_set import ObservationSetCsvConverter, \
    FeatureSetCsvConverter, \
    ObservationSetListConverter, \
    FeatureSetListConverter

from api.converters.json_converters import JsonConverter

from api.tests.base import BaseAPITestCase


class TestBasicAttributeConverter(BaseAPITestCase):

    def test_basic_attributes(self):
        s = StringConverter()
        v = s.convert_input('abc', '', '')
        self.assertEqual(v, 'abc')
        v = s.convert_output('','','', 'abc')
        self.assertEqual(v, 'abc')

        v = s.convert_input('ab c', '', '')
        self.assertEqual(v, 'ab_c')
        v = s.convert_output('','','', 'ab c')
        self.assertEqual(v, 'ab_c')

        with self.assertRaises(AttributeValueError):
            v = s.convert_input('ab?c', '', '')

        with self.assertRaises(AttributeValueError):
            v = s.convert_output('','','', 'ab?c')

        s = UnrestrictedStringConverter()
        v = s.convert_input('abc', '', '')
        self.assertEqual(v, 'abc')
        v = s.convert_output('','','', 'abc')
        self.assertEqual(v, 'abc')

        v = s.convert_input('ab c', '', '')
        self.assertEqual(v, 'ab c')
        v = s.convert_output('','','', 'ab c')
        self.assertEqual(v, 'ab c')

        v = s.convert_input('ab?c', '', '')
        self.assertEqual(v, 'ab?c')
        v = s.convert_output('','','', 'ab?c')
        self.assertEqual(v, 'ab?c')

        ic = IntegerConverter()
        i = ic.convert_input( 2, '', '')
        self.assertEqual(i,2)
        i = ic.convert_output('','','', 2)
        self.assertEqual(i,2)

        with self.assertRaises(AttributeValueError):
            ic.convert_input('1', '', '')
        with self.assertRaises(AttributeValueError):
            ic.convert_input(1.2, '', '')
        with self.assertRaises(AttributeValueError):
            ic.convert_output('','','','1')
        with self.assertRaises(AttributeValueError):
            ic.convert_output('','','',1.2)

        with self.assertRaises(AttributeValueError):
            ic.convert_input('a', '', '')

        with self.assertRaises(AttributeValueError):
            ic.convert_output('', '', '', 'a')

        s = StringListConverter()
        v = s.convert_input( ['ab','c d'], '', '')
        self.assertCountEqual(['ab','c_d'], v)
        v = s.convert_output('','','', ['ab','c d'])
        self.assertCountEqual(['ab','c_d'], v)

        with self.assertRaises(DataStructureValidationException):
            v = s.convert_input( 2, '', '')

        with self.assertRaises(DataStructureValidationException):
            s.convert_output('', '', '', 2)

        v = s.convert_input( ['1','2'], '', '')
        self.assertCountEqual(['1','2'], v)

        v = s.convert_output('', '', '', ['1','2'])
        self.assertCountEqual(['1','2'], v)

        s = UnrestrictedStringListConverter()
        v = s.convert_input( ['ab','c d'], '', '')
        self.assertCountEqual(['ab','c d'], v)
        v = s.convert_output('','','', ['ab','c d'])
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

    def test_single_local_input_converter(self):
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
        x = c.convert_input(user_input, '', mock_staging_dir)
        self.assertEqual(x, mock_path)
        mock_convert_resource_input.assert_called_once_with(
            user_input, mock_staging_dir)

    @mock.patch('api.converters.data_resource.ResourceMetadata')
    @mock.patch('api.converters.data_resource.retrieve_resource_class_standard_format')
    @mock.patch('api.converters.data_resource.initiate_resource_validation')
    def test_single_local_output_converter(self, 
        mock_initiate_resource_validation,
        mock_retrieve_resource_class_standard_format,
        mock_resource_metadata_class):
        '''
        Tests the conversion of a single output for a local 
        runner. Mocks out the actual resource creation and 
        some methods, but asserts that they are called with the
        expected args.

        This test is for a DataResource which has a fixed
        resource_type defined by the output spec.
        '''

        mock_retrieve_resource_class_standard_format.return_value = 'TSV'
        c = LocalDockerSingleDataResourceConverter()

        # mock out the actual creation of the Resource
        resource_pk = uuid.uuid4()
        mock_create_resource = mock.MagicMock()
        mock_resource = mock.MagicMock()
        mock_resource.pk = resource_pk
        mock_create_resource.return_value = mock_resource
        mock_create_output_filename = mock.MagicMock()
        mock_name = 'foo'
        mock_create_output_filename.return_value = mock_name
        mock_executed_op = mock.MagicMock()
        mock_executed_op.job_name = 'myjob'
        mock_workspace = mock.MagicMock()
        c._create_resource = mock_create_resource
        c._create_output_filename = mock_create_output_filename

        # need a valid data_resources.operation_output.OperationOutput
        # instance:
        d = {
            'required': True,
            'converter': '',
            'spec': {
                "attribute_type": "DataResource",
                "many": False,
                "resource_type": "MTX"
            }
        }
        o = OperationOutput(d)

        # now call the converter
        mock_path = '/some/path'
        u = c.convert_output(mock_executed_op, mock_workspace, o, mock_path)
        self.assertEqual(u, str(resource_pk))
        c._create_resource.assert_called_once_with(
            mock_executed_op,
            mock_workspace,
            mock_path,
            mock_name
        )
        mock_retrieve_resource_class_standard_format.assert_called_once_with('MTX')
        mock_initiate_resource_validation.assert_called_once_with(
            mock_resource,
            'MTX',
            'TSV'
        )
        self.assertTrue(mock_resource.is_active)
        mock_resource.save.assert_called()

    @mock.patch('api.converters.data_resource.ResourceMetadata')
    @mock.patch('api.converters.data_resource.retrieve_resource_class_standard_format')
    @mock.patch('api.converters.data_resource.initiate_resource_validation')
    def test_single_local_output_variable_data_resource_converter(self, 
        mock_initiate_resource_validation,
        mock_retrieve_resource_class_standard_format,
        mock_resource_metadata_class):
        '''
        Tests the conversion of a single output for a local 
        runner. Mocks out the actual resource creation and 
        some methods, but asserts that they are called with the
        expected args.

        This tests for VariableDataResource types which can have
        multiple potential output resource_types
        '''

        mock_retrieve_resource_class_standard_format.return_value = 'TSV'
        c = LocalDockerSingleVariableDataResourceConverter()

        # mock out the actual creation of the Resource
        resource_pk = uuid.uuid4()
        mock_create_resource = mock.MagicMock()
        mock_resource = mock.MagicMock()
        mock_resource.pk = resource_pk
        mock_create_resource.return_value = mock_resource
        mock_create_output_filename = mock.MagicMock()
        mock_name = 'foo'
        mock_create_output_filename.return_value = mock_name
        mock_executed_op = mock.MagicMock()
        mock_executed_op.job_name = 'myjob'
        mock_workspace = mock.MagicMock()
        c._create_resource = mock_create_resource
        c._create_output_filename = mock_create_output_filename

        # need a valid data_resources.operation_output.OperationOutput
        # instance:
        d = {
            'required': True,
            'converter': '',
            'spec': {
                "attribute_type": "VariableDataResource",
                "many": False,
                "resource_types": ["I_MTX","MTX"]
            }
        }
        o = OperationOutput(d)

        # now call the converter
        mock_path = '/some/path'
        operation_output_payload = {
            'path': mock_path,
            'resource_type': "I_MTX"
        }
        u = c.convert_output(mock_executed_op, mock_workspace, o, operation_output_payload)
        self.assertEqual(u, str(resource_pk))
        c._create_resource.assert_called_once_with(
            mock_executed_op,
            mock_workspace,
            mock_path,
            mock_name
        )
        mock_retrieve_resource_class_standard_format.assert_called_once_with('I_MTX')
        mock_initiate_resource_validation.assert_called_once_with(
            mock_resource,
            'I_MTX',
            'TSV'
        )
        self.assertTrue(mock_resource.is_active)
        mock_resource.save.assert_called()

        # try with an invalid resource type
        mock_create_resource.reset_mock()
        mock_retrieve_resource_class_standard_format.reset_mock()
        mock_initiate_resource_validation.reset_mock()
        mock_resource.reset_mock()
        operation_output_payload = {
            'path': mock_path,
            'resource_type': "FT"
        }
        with self.assertRaisesRegex(OutputConversionException, 'not consistent'):
            u = c.convert_output(mock_executed_op, mock_workspace, o, operation_output_payload)

        c._create_resource.assert_not_called()
        mock_retrieve_resource_class_standard_format.assert_not_called()
        mock_initiate_resource_validation.assert_not_called()

    @mock.patch('api.converters.data_resource.ResourceMetadata')
    @mock.patch('api.converters.data_resource.retrieve_resource_class_standard_format')
    @mock.patch('api.converters.data_resource.initiate_resource_validation')
    def test_single_local_output_converter_failure(self, 
        mock_initiate_resource_validation,
        mock_retrieve_resource_class_standard_format,
        mock_resource_metadata_class):
        '''
        Tests the conversion of a single output for a local 
        runner. Here, we mock there being an issue
        '''

        mock_retrieve_resource_class_standard_format.return_value = 'TSV'
        # need a valid data_resources.operation_output.OperationOutput
        # instance:
        d = {
            'required': True,
            'converter': '',
            'spec': {
                "attribute_type": "DataResource",
                "many": False,
                "resource_type": "MTX"
            }
        }
        o = OperationOutput(d)

        c1 = LocalDockerSingleDataResourceConverter()
        c2 = CromwellSingleDataResourceConverter()
        for c in [c1, c2]:

            # mock out the actual creation of the Resource
            mock_create_resource = mock.MagicMock()
            mock_create_resource.side_effect = StorageException('!!')

            mock_create_output_filename = mock.MagicMock()
            mock_name = 'foo'
            mock_create_output_filename.return_value = mock_name

            mock_executed_op = mock.MagicMock()
            mock_executed_op.job_name = 'myjob'
            mock_workspace = mock.MagicMock()
            mock_handle_storage_failure = mock.MagicMock()

            c._create_resource = mock_create_resource
            c._create_output_filename = mock_create_output_filename
            c._handle_storage_failure = mock_handle_storage_failure

            mock_retrieve_resource_class_standard_format.reset_mock()
            mock_initiate_resource_validation.reset_mock()

            # now call the converter
            mock_path = '/some/path'
            u = c.convert_output(mock_executed_op, mock_workspace, o, mock_path)
            self.assertIsNone(u)
            c._create_resource.assert_called_once_with(
                mock_executed_op,
                mock_workspace,
                mock_path,
                mock_name
            )
            mock_retrieve_resource_class_standard_format.assert_not_called()
            mock_initiate_resource_validation.assert_not_called()

    @mock.patch('api.converters.data_resource.ResourceMetadata')
    @mock.patch('api.converters.data_resource.retrieve_resource_class_standard_format')
    @mock.patch('api.converters.data_resource.initiate_resource_validation')
    def test_single_local_output_converter_validation_failure(self, 
        mock_initiate_resource_validation,
        mock_retrieve_resource_class_standard_format,
        mock_resource_metadata_class):
        '''
        Tests the case where a validation failure occurs.
        '''

        mock_retrieve_resource_class_standard_format.return_value = 'TSV'

        # need a valid data_resources.operation_output.OperationOutput
        # instance:
        d = {
            'required': True,
            'converter': '',
            'spec': {
                "attribute_type": "DataResource",
                "many": False,
                "resource_type": "MTX"
            }
        }
        o = OperationOutput(d)

        c1 = LocalDockerSingleDataResourceConverter()
        c2 = CromwellSingleDataResourceConverter()
        for c in [c1, c2]:

            # mock out the actual creation of the Resource
            resource_pk = uuid.uuid4()
            mock_create_resource = mock.MagicMock()
            mock_resource = mock.MagicMock()
            mock_resource.pk = resource_pk
            mock_create_resource.return_value = mock_resource
            mock_create_output_filename = mock.MagicMock()
            mock_name = 'foo'
            mock_create_output_filename.return_value = mock_name
            mock_executed_op = mock.MagicMock()
            mock_executed_op.job_name = 'myjob'
            mock_workspace = mock.MagicMock()
            mock_handle_invalid_resource_type = mock.MagicMock()
            c._create_resource = mock_create_resource
            c._create_output_filename = mock_create_output_filename
            c._handle_invalid_resource_type = mock_handle_invalid_resource_type

            mock_retrieve_resource_class_standard_format.reset_mock()
            mock_initiate_resource_validation.reset_mock()

            mock_initiate_resource_validation.side_effect = Exception('!!!')

            # now call the converter
            mock_path = '/some/path'
            with self.assertRaisesRegex(OutputConversionException, 'Failed to validate'):
                u = c.convert_output(mock_executed_op, mock_workspace, o, mock_path)

            c._create_resource.assert_called_once_with(
                mock_executed_op,
                mock_workspace,
                mock_path,
                mock_name
            )
            mock_retrieve_resource_class_standard_format.assert_called_once_with('MTX')
            mock_initiate_resource_validation.assert_called_once_with(
                mock_resource,
                'MTX',
                'TSV'
            )

    def test_single_local_with_rt_input_input_converter(self):
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

    def test_single_cromwell_input_converter(self):
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
        
        x = c.convert_input( uuid_list, '', '/some/staging_dir/')
        self.assertEqual(x, mock_path_list)

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

    @mock.patch('api.converters.data_resource.ResourceMetadata')
    @mock.patch('api.converters.data_resource.retrieve_resource_class_standard_format')
    @mock.patch('api.converters.data_resource.initiate_resource_validation')
    def test_multiple_local_output_converter(self, 
        mock_initiate_resource_validation,
        mock_retrieve_resource_class_standard_format,
        mock_resource_metadata_class):
        '''
        Tests the proper steps are performed for converting 
        multiple local outputs.
        '''

        mock_retrieve_resource_class_standard_format.return_value = 'TSV'

        # need a valid data_resources.operation_output.OperationOutput
        # instance:
        d = {
            'required': True,
            'converter': '',
            'spec': {
                "attribute_type": "DataResource",
                "many": True,
                "resource_type": "MTX"
            }
        }
        o = OperationOutput(d)

        c1 = LocalDockerMultipleDataResourceConverter()
        c2 = CromwellMultipleDataResourceConverter()
        for c in [c1, c2]:

            # mock there being two resources to create
            all_resource_pk = [
                uuid.uuid4(),
                uuid.uuid4()
            ]
            mock_create_resource = mock.MagicMock()
            mock_resource1 = mock.MagicMock()
            mock_resource1.pk = all_resource_pk[0]
            mock_resource2 = mock.MagicMock()
            mock_resource2.pk = all_resource_pk[1]
            mock_create_resource.side_effect = [mock_resource1, mock_resource2]
            mock_create_output_filename = mock.MagicMock()
            mock_name1 = 'foo'
            mock_name2 = 'bar'
            mock_create_output_filename.side_effect = [mock_name1, mock_name2]
            mock_executed_op = mock.MagicMock()
            mock_executed_op.job_name = 'myjob'
            mock_workspace = mock.MagicMock()
            c._create_resource = mock_create_resource
            c._create_output_filename = mock_create_output_filename

            # call reset on the mocked functions that are used 
            # on each loop:
            mock_retrieve_resource_class_standard_format.reset_mock()
            mock_initiate_resource_validation.reset_mock()

            # now call the converter
            mock_paths = ['/some/path1', 'some/path2']
            u = c.convert_output(mock_executed_op, mock_workspace, o, mock_paths)
            self.assertCountEqual(u, [str(x) for x in all_resource_pk])
            c._create_resource.assert_has_calls([
                mock.call(
                    mock_executed_op,
                    mock_workspace,
                    mock_paths[0],
                    mock_name1
                ),
                mock.call(
                    mock_executed_op,
                    mock_workspace,
                    mock_paths[1],
                    mock_name2
                ),
            ])

            mock_retrieve_resource_class_standard_format.assert_has_calls([
                mock.call('MTX'), mock.call('MTX')])

            mock_initiate_resource_validation.assert_has_calls([
                mock.call(
                    mock_resource1,
                    'MTX',
                    'TSV'),
                mock.call(
                    mock_resource2,
                    'MTX',
                    'TSV'),
            ])
            self.assertTrue(mock_resource1.is_active)
            mock_resource1.save.assert_called()
            self.assertTrue(mock_resource2.is_active)
            mock_resource2.save.assert_called()

    @mock.patch('api.converters.data_resource.ResourceMetadata')
    @mock.patch('api.converters.data_resource.retrieve_resource_class_standard_format')
    @mock.patch('api.converters.data_resource.initiate_resource_validation')
    @mock.patch('api.converters.data_resource.delete_resource_by_pk')
    def test_multiple_local_output_converter_failure(self, 
        mock_delete_resource_by_pk,
        mock_initiate_resource_validation,
        mock_retrieve_resource_class_standard_format,
        mock_resource_metadata_class):
        '''
        Tests that we handle cleanup of other outputs if one of 
        them fails. Here, we mock there being a storage problem on
        one of multiple files corresponding to a single input.
        Since the output was marked as required, we check that
        an exception is raised and we delete the other resource
        so as not to create an incomplete output state.
        '''

        mock_retrieve_resource_class_standard_format.return_value = 'TSV'
        # need a valid data_resources.operation_output.OperationOutput
        # instance:
        d = {
            'required': True,
            'converter': '',
            'spec': {
                "attribute_type": "DataResource",
                "many": True,
                "resource_type": "MTX"
            }
        }
        o = OperationOutput(d)
        c1 = LocalDockerMultipleDataResourceConverter()
        c2 = CromwellMultipleDataResourceConverter()
        for c in [c1, c2]:

            # mock there being two resources to create
            all_resource_pk = [
                uuid.uuid4(),
                uuid.uuid4()
            ]
            mock_create_resource = mock.MagicMock()
            mock_resource1 = mock.MagicMock()
            mock_resource1.pk = all_resource_pk[0]
            mock_create_resource.side_effect = [
                mock_resource1, StorageException('!!')]
            mock_create_output_filename = mock.MagicMock()
            mock_name1 = 'foo'
            mock_name2 = 'bar'
            mock_create_output_filename.side_effect = [mock_name1, mock_name2]
            mock_executed_op = mock.MagicMock()
            mock_executed_op.job_name = 'myjob'
            mock_workspace = mock.MagicMock()
            c._create_resource = mock_create_resource
            c._create_output_filename = mock_create_output_filename

            # call reset on the mocked functions that are used 
            # on each loop:
            mock_retrieve_resource_class_standard_format.reset_mock()
            mock_initiate_resource_validation.reset_mock()

            # now call the converter
            # even though this test is checking for proper behavior with
            # both local and Cromwell converters, these paths don't 
            # actually matter in their content:
            mock_paths = ['/some/path1', 'some/path2']
            with self.assertRaisesRegex(OutputConversionException, 'Failed to convert'):
                c.convert_output(mock_executed_op, mock_workspace, o, mock_paths)
            c._create_resource.assert_has_calls([
                mock.call(
                    mock_executed_op,
                    mock_workspace,
                    mock_paths[0],
                    mock_name1
                ),
                mock.call(
                    mock_executed_op,
                    mock_workspace,
                    mock_paths[1],
                    mock_name2
                ),
            ])
            mock_retrieve_resource_class_standard_format.assert_has_calls([
                mock.call('MTX')])
            mock_initiate_resource_validation.assert_has_calls([
                mock.call(
                    mock_resource1,
                    'MTX',
                    'TSV'),
            ])
            self.assertTrue(mock_resource1.is_active)
            mock_resource1.save.assert_called()
            mock_delete_resource_by_pk.assert_has_calls([
                mock.call(str(all_resource_pk[0]))
            ])

    @mock.patch('api.converters.data_resource.ResourceMetadata')
    @mock.patch('api.converters.data_resource.retrieve_resource_class_standard_format')
    @mock.patch('api.converters.data_resource.initiate_resource_validation')
    @mock.patch('api.converters.data_resource.delete_resource_by_pk')
    def test_multiple_output_converter_failure_for_optional(self, 
        mock_delete_resource_by_pk,
        mock_initiate_resource_validation,
        mock_retrieve_resource_class_standard_format,
        mock_resource_metadata_class):
        '''
        Here, we mock there being a storage problem on
        one of multiple files corresponding to a single input.
        Since the output was NOT marked as required, we don't
        raise any exceptions
        '''

        mock_retrieve_resource_class_standard_format.return_value = 'TSV'

        # need a valid data_resources.operation_output.OperationOutput
        # instance:
        d = {
            'required': False, #<--- important!
            'converter': '',
            'spec': {
                "attribute_type": "DataResource",
                "many": True,
                "resource_type": "MTX"
            }
        }
        o = OperationOutput(d)
        c1 = LocalDockerMultipleDataResourceConverter()
        c2 = CromwellMultipleDataResourceConverter()
        for c in [c1, c2]:

            # mock there being two resources to create
            all_resource_pk = [
                uuid.uuid4(),
                uuid.uuid4()
            ]
            mock_create_resource = mock.MagicMock()
            mock_resource1 = mock.MagicMock()
            mock_resource1.pk = all_resource_pk[0]
            mock_create_resource.side_effect = [
                mock_resource1, StorageException('!!')]
            mock_create_output_filename = mock.MagicMock()
            mock_name1 = 'foo'
            mock_name2 = 'bar'
            mock_create_output_filename.side_effect = [mock_name1, mock_name2]
            mock_executed_op = mock.MagicMock()
            mock_executed_op.job_name = 'myjob'
            mock_workspace = mock.MagicMock()
            mock_clean = mock.MagicMock()
            c._create_resource = mock_create_resource
            c._create_output_filename = mock_create_output_filename
            c._cleanup_other_outputs = mock_clean

            # call reset on the mocked functions that are used 
            # on each loop:
            mock_retrieve_resource_class_standard_format.reset_mock()
            mock_initiate_resource_validation.reset_mock()

            # now call the converter
            # even though this test is checking for proper behavior with
            # both local and Cromwell converters, these paths don't 
            # actually matter in their content:
            mock_paths = ['/some/path1', 'some/path2']
            u = c.convert_output(mock_executed_op, mock_workspace, o, mock_paths)
            self.assertCountEqual(u, [str(all_resource_pk[0]), None])
            c._create_resource.assert_has_calls([
                mock.call(
                    mock_executed_op,
                    mock_workspace,
                    mock_paths[0],
                    mock_name1
                ),
                mock.call(
                    mock_executed_op,
                    mock_workspace,
                    mock_paths[1],
                    mock_name2
                ),
            ])
            mock_retrieve_resource_class_standard_format.assert_has_calls([
                mock.call('MTX')])
            mock_initiate_resource_validation.assert_has_calls([
                mock.call(
                    mock_resource1,
                    'MTX',
                    'TSV'),
            ])
            self.assertTrue(mock_resource1.is_active)
            mock_resource1.save.assert_called()
            mock_clean.assert_not_called()


    def test_cromwell_converters_case2(self):
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

class TestJsonConverter(BaseAPITestCase):

    def test_json_output(self):
        '''
        Tools can output a nested json data structure. That is,
        for local outputs, we have `outputs.json` which contains
        information like paths to output files, etc.

        Inside that, a key can address a json structure.

        Note that failures to properly nest the JSON will raise 
        exceptions when the file is read by the built-in json lib.

        This catches the situation where the addressed item is not,
        in fact, valid json
        '''
        
        c = JsonConverter()
        mock_executed_op = mock.MagicMock()
        mock_workspace = mock.MagicMock()
        o = None
        j = 'abc'
        with self.assertRaises(json.decoder.JSONDecodeError):
            c.convert_output(mock_executed_op, mock_workspace, o, j)
