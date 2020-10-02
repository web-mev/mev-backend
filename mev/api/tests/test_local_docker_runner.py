import unittest
import unittest.mock as mock
import os
import json
import copy
import uuid
import shutil
import datetime 

from django.core.exceptions import ImproperlyConfigured

from api.tests.base import BaseAPITestCase
from api.utilities.operations import read_operation_json
from api.runners.local_docker import LocalDockerRunner
from api.models import Resource

# the api/tests dir
TESTDIR = os.path.dirname(__file__)
TESTDIR = os.path.join(TESTDIR, 'operation_test_files')

class LocalDockerRunnerTester(BaseAPITestCase):

    def setUp(self):
        self.filepath = os.path.join(TESTDIR, 'valid_operation.json')

    @mock.patch('api.runners.local_docker.copy_local_resource')
    def test_copy_data_resources(self, mock_copy_local_resource):
        '''
        To execute Operations within a controlled environment, we copy
        the necessary files out of the user's local cache into an execution
        folder. Check that the proper copy calls are made
        '''

        op_data = read_operation_json(self.filepath)
        runner = LocalDockerRunner()

        # this is a mock version of how the inputs would look after they were
        # properly converted for the runner. Note that the keys below need
        # to match those in the mock operation file (location at self.filepath)
        arg_dict = {
            'count_matrix': '/path/to/local/cache/foo.tsv',
            'p_val': 0.05
        }
        exec_dir = '/some/dir'
        runner._copy_data_resources(exec_dir, op_data, arg_dict)
        self.assertEqual(arg_dict['count_matrix'], os.path.join(exec_dir, 'foo.tsv'))

    @mock.patch('api.runners.local_docker.OperationRunner.CONVERTER_FILE', 
        new_callable=mock.PropertyMock, 
        return_value='bad_converters.json')
    def test_handles_bad_converter_gracefully(self, mock_OperationRunner):
        '''
        In the case that a converter class is not found for the input, see that we
        handle this error appropriately.
        '''
        # need a resource to populate the field
        all_r = Resource.objects.all()
        r = all_r[0]
        inputs = {
            'count_matrix': str(r.id),
            'p_val': 0.05
        }
        runner = LocalDockerRunner()
        with self.assertRaises(Exception):
            runner._map_inputs(TESTDIR, inputs)

    @mock.patch('api.runners.local_docker.check_container_exit_code')
    @mock.patch('api.runners.local_docker.get_finish_datetime')
    @mock.patch('api.runners.local_docker.remove_container')
    def test_handles_job_failure(self, mock_remove_container, mock_get_finish_datetime, mock_check_container_exit_code):
        '''
        If a job fails, the container should issue a non-zero exit code
        If that happens, test that we handle the failure appropriately and
        set the proper fields on the database object
        '''
        runner = LocalDockerRunner()
        mock_executed_op = mock.MagicMock()
        u = str(uuid.uuid4())
        mock_executed_op.job_id = u

        mock_get_finish_datetime.return_value = datetime.datetime.now()
        mock_check_container_exit_code.return_value = 1

        runner.finalize(mock_executed_op)
        mock_executed_op.save.assert_called()
        mock_remove_container.assert_called()
        self.assertTrue(mock_executed_op.job_failed)

    @mock.patch('api.runners.local_docker.check_container_exit_code')
    @mock.patch('api.runners.local_docker.get_finish_datetime')
    @mock.patch('api.runners.local_docker.remove_container')
    @mock.patch('api.runners.local_docker.get_operation_instance_data')
    @mock.patch('api.runners.local_docker.LocalDockerOutputConverter')
    def test_handles_job_finalization(self, \
        mock_LocalDockerOutputConverter, \
        mock_get_operation_instance_data, \
        mock_remove_container, \
        mock_get_finish_datetime, \
        mock_check_container_exit_code):
        '''
        If a job succeeds, check that we call all the right functions
        '''
        runner = LocalDockerRunner()
        mock_load_outputs = mock.MagicMock()
        mock_load_outputs.return_value = {
            'abc': 123
        }
        runner.load_outputs_file = mock_load_outputs

        mock_get_operation_instance_data.return_value = {
            'outputs': {
                'abc': {
                    "spec": {
                        'attribute_type': 'Integer'
                    }
                }
            }
        }

        mock_executed_op = mock.MagicMock()
        u = str(uuid.uuid4())
        mock_executed_op.job_id = u
        mock_workspace = mock.MagicMock()
        mock_executed_op.workspace = mock_workspace

        converter_instance = mock.MagicMock()
        converter_instance.convert_output.return_value = 456
        mock_LocalDockerOutputConverter.return_value = converter_instance

        mock_get_finish_datetime.return_value = datetime.datetime.now()
        mock_check_container_exit_code.return_value = 0

        runner.finalize(mock_executed_op)
        mock_executed_op.save.assert_called()
        mock_remove_container.assert_called()
        self.assertFalse(mock_executed_op.job_failed)
        self.assertDictEqual(mock_executed_op.outputs,{'abc': 456})


    @mock.patch('api.runners.local_docker.check_container_exit_code')
    @mock.patch('api.runners.local_docker.get_finish_datetime')
    @mock.patch('api.runners.local_docker.remove_container')
    @mock.patch('api.runners.local_docker.get_operation_instance_data')
    @mock.patch('api.runners.local_docker.LocalDockerOutputConverter')
    @mock.patch('api.runners.local_docker.alert_admins')
    def test_handles_extra_output_on_job_finalization(self, \
        mock_alert_admins, \
        mock_LocalDockerOutputConverter, \
        mock_get_operation_instance_data, \
        mock_remove_container, \
        mock_get_finish_datetime, \
        mock_check_container_exit_code):
        '''
        If a job succeeds, but an output is unknown, we handle this
        '''
        runner = LocalDockerRunner()
        mock_load_outputs = mock.MagicMock()
        mock_load_outputs.return_value = {
            'abc': 123,
            'def': 'xyz'
        }
        runner.load_outputs_file = mock_load_outputs

        # the expected outputs have key 'abc', but not 'def'
        mock_get_operation_instance_data.return_value = {
            'outputs': {
                'abc': {
                    "spec": {
                        'attribute_type': 'Integer'
                    }
                }
            }
        }

        mock_executed_op = mock.MagicMock()
        u = str(uuid.uuid4())
        mock_executed_op.job_id = u
        mock_workspace = mock.MagicMock()
        mock_executed_op.workspace = mock_workspace

        converter_instance = mock.MagicMock()
        converter_instance.convert_output.return_value = 456
        mock_LocalDockerOutputConverter.return_value = converter_instance

        mock_get_finish_datetime.return_value = datetime.datetime.now()
        mock_check_container_exit_code.return_value = 0

        runner.finalize(mock_executed_op)
        mock_alert_admins.assert_called()
        mock_executed_op.save.assert_called()
        mock_remove_container.assert_called()
        self.assertFalse(mock_executed_op.job_failed)

        # the 'extra' "def" key not included in the outputs
        self.assertDictEqual(mock_executed_op.outputs,{'abc': 456})