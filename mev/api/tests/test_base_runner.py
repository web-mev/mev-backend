import unittest
import unittest.mock as mock
import os
import json
import copy
import uuid
import shutil

from django.core.exceptions import ImproperlyConfigured

from api.tests.base import BaseAPITestCase
from api.utilities.operations import read_operation_json
from api.runners.base import OperationRunner
from api.models import Resource
from api.exceptions import OutputConversionException

# the api/tests dir
TESTDIR = os.path.dirname(__file__)
TESTDIR = os.path.join(TESTDIR, 'operation_test_files')

class BaseRunnerTester(BaseAPITestCase):

    def setUp(self):
        filepath = os.path.join(TESTDIR, 'multiresource_output.json')
        fp = open(filepath)
        self.op_data= json.load(fp)
        fp.close()

        filepath = os.path.join(TESTDIR, 'valid_workspace_operation.json')
        fp = open(filepath)
        self.op_data2= json.load(fp)
        fp.close()

    @mock.patch('api.runners.base.OperationRunner._get_converter_dict')
    @mock.patch('api.runners.base.import_string')
    def test_input_mapping(self, mock_import_string, mock_get_converter_dict):

        final_path = '/some/file/path.txt'
        mock_converter1_class = mock.MagicMock()
        mock_converter2_class = mock.MagicMock()
        mock_converter1 = mock.MagicMock()
        mock_converter2 = mock.MagicMock()
        mock_converter1.convert.return_value = {'count_matrix': final_path}
        mock_converter2.convert.return_value = {'p_val': 0.01}
        mock_converter1_class.return_value = mock_converter1
        mock_converter2_class.return_value = mock_converter2
        mock_import_string.side_effect = [mock_converter1_class, mock_converter2_class]

        mock_get_converter_dict.return_value = {
            'count_matrix': 'api.converters.data_resource.LocalDockerSingleDataResourceConverter',
            'p_val': 'api.converters.basic_attributes.BoundedFloatAttributeConverter'
        }
        r = Resource.objects.all()[0]
        validated_inputs = {
            'count_matrix': str(r.pk),
            'p_val': 0.01 
        }
        runner = OperationRunner()
        mock_op_dir = '/some/op/dir'
        converted_inputs = runner._map_inputs(mock_op_dir, validated_inputs, '')
        expected_outputs = {
            'count_matrix': final_path,
            'p_val': 0.01 
        }
        self.assertDictEqual(converted_inputs, expected_outputs)

    @mock.patch('api.runners.base.OperationRunner._get_converter_dict')
    @mock.patch('api.runners.base.os.path.exists')
    def test_bad_converter_class(self, mock_os_exists, mock_get_converter_dict):
        '''
        Test that a bad converter class will raise an exception
        '''
        runner = OperationRunner()
        mock_get_converter_dict.return_value = {'a': 'some junk'}
        with self.assertRaises(Exception):
            runner.check_required_files('')

    @mock.patch('api.runners.base.get_operation_instance_data')
    @mock.patch('api.runners.base.alert_admins')
    def test_bad_keys(self, mock_alert_admins, mock_get_operation_instance_data):
        '''
        This tests that differing keys between the operation spec 
        and the actual outputs are handled appropriately.
        '''

        mock_get_operation_instance_data.return_value = self.op_data
        runner = OperationRunner()
        mock_cleanup = mock.MagicMock()
        runner.cleanup_on_error = mock_cleanup

        # this is missing a dge_table key
        bad_outputs = {
            "norm_counts": "/path/to/norm_counts.tsv"
        }
        mock_executed_op = mock.MagicMock()
        mock_executed_op.operation.id = 'abc'
        mock_converter =  mock.MagicMock()
        with self.assertRaisesRegex(OutputConversionException, 
        'Could not locate the output') as ex:
            runner.convert_outputs(
                mock_executed_op,
                mock_converter,
                bad_outputs
            )

        mock_cleanup.assert_called_with(
            self.op_data['outputs'],
            {}
        )
        mock_alert_admins.assert_called()

        # run another test here-- now there will be a
        # resource which needs cleanup so that we don't leave any 
        # 'hanging' outputs.
        mock_cleanup.reset_mock()
        mock_alert_admins.reset_mock()

        # this is missing a norm_counts key
        bad_outputs = {
            "dge_table": "/path/to/dge.tsv"
        }
        mock_executed_op = mock.MagicMock()
        mock_executed_op.operation.id = 'abc'
        mock_converter =  mock.MagicMock()
        u = str(uuid.uuid4())
        mock_converter.convert_output.return_value = u
        with self.assertRaisesRegex(OutputConversionException, 
        'Could not locate the output') as ex:
            runner.convert_outputs(
                mock_executed_op,
                mock_converter,
                bad_outputs
            )
        mock_cleanup.assert_called_with(
            self.op_data['outputs'],
            {
                'dge_table': u
            }
        )
        mock_alert_admins.assert_called()

    @mock.patch('api.runners.base.get_operation_instance_data')
    def test_output_conversion(self, mock_get_operation_instance_data):
        '''
        This tests that proper/valid output conversions go as planned
        '''

        mock_get_operation_instance_data.return_value = self.op_data

        runner = OperationRunner()
        mock_cleanup = mock.MagicMock()
        runner.cleanup_on_error = mock_cleanup

        # these outputs correspond to the multiresource_output.json
        outputs = {
            "norm_counts": "/path/to/norm_counts.tsv" ,
            "dge_table": {
                "path": "/path/to/dge_table.tsv",
                "resource_type": "MTX"
            }
        }
        u1 = str(uuid.uuid4())
        u2 = str(uuid.uuid4())
        mock_converter =  mock.MagicMock()
        # The ordering below is set b/c the convert_outputs
        # performs a sort on the keys of the operation's output spec
        mock_converter.convert_output.side_effect = [
            u1, # this will be the UUID for dge_Table
            u2 # the UUID for norm_counts
        ]

        mock_executed_op = mock.MagicMock()
        mock_executed_op.operation.id = 'abc'

        d = runner.convert_outputs(
            mock_executed_op,
            mock_converter,
            outputs
        )
        self.assertDictEqual(
            d,
            {
                'norm_counts': u2,
                'dge_table': u1
            }
        )
        mock_cleanup.assert_not_called()

    @mock.patch('api.runners.base.get_operation_instance_data')
    def test_output_conversion_error(self, mock_get_operation_instance_data):
        '''
        If any of the outputs do not pass validation (either b/c the tool developer
        did not create outputs.json correctly OR the file is corrupted and doesn't
        pass validation) then we have to do some cleanup so we don't have 'incomplete'
        outputs. If only a portion of the outputs validated, the final results may not
        make sense.

        This test checks that the cleanup method is called when an error occurs. Here, since
        the first output fails validation, there is effectively nothing to clean up. (Recall that 
        the cleanup method here really only operates on OTHER inputs which did validate
        successfully)
        '''

        mock_get_operation_instance_data.return_value = self.op_data2

        runner = OperationRunner()
        mock_cleanup = mock.MagicMock()
        runner.cleanup_on_error = mock_cleanup

        # these outputs correspond to the multiresource_output.json
        outputs = {
            "norm_counts": "/path/to/norm_counts.tsv" ,
            "dge_table": "/path/to/dge.tsv"
        }
        u = str(uuid.uuid4())
        mock_converter =  mock.MagicMock()
        mock_converter.convert_output.side_effect = [
            OutputConversionException('ack'),
            OutputConversionException('ack')
        ]

        mock_executed_op = mock.MagicMock()
        mock_executed_op.operation.id = 'abc'

        with self.assertRaises(OutputConversionException) as ex:
            runner.convert_outputs(
                mock_executed_op,
                mock_converter,
                outputs
            )

        mock_cleanup.assert_called_with(
            self.op_data2['outputs'],
            {}
        )

    @mock.patch('api.runners.base.get_operation_instance_data')
    def test_output_conversion_error_case2(self, mock_get_operation_instance_data):
        '''
        If any of the outputs do not pass validation (either b/c the tool developer
        did not create outputs.json correctly OR the file is corrupted and doesn't
        pass validation) then we have to do some cleanup so we don't have 'incomplete'
        outputs. If only a portion of the outputs validated, the final results may not
        make sense.

        This test checks that the cleanup method is called when an error occurs
        '''

        mock_get_operation_instance_data.return_value = self.op_data

        runner = OperationRunner()
        mock_cleanup = mock.MagicMock()
        runner.cleanup_on_error = mock_cleanup

        # these outputs correspond to the multiresource_output.json
        outputs = {
            "norm_counts": "/path/to/norm_counts.tsv" ,
            "dge_table": {
                "path": "/path/to/dge_table.tsv",
                "resource_type": "MTX"
            }
        }
        u = str(uuid.uuid4())
        mock_converter =  mock.MagicMock()
        mock_converter.convert_output.side_effect = [
            u,
            OutputConversionException('ack')
        ]

        mock_executed_op = mock.MagicMock()
        mock_executed_op.operation.id = 'abc'

        with self.assertRaises(OutputConversionException) as ex:
            runner.convert_outputs(
                mock_executed_op,
                mock_converter,
                outputs
            )

        mock_cleanup.assert_called_with(
            self.op_data['outputs'],
            {
                'dge_table': u
            }
        )


   