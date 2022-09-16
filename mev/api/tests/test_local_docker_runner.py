import unittest
import unittest.mock as mock
import os
import json
import copy
import uuid
import shutil
import datetime 

from django.core.exceptions import ImproperlyConfigured

from api.exceptions import OutputConversionException
from api.tests.base import BaseAPITestCase
from api.utilities.operations import read_operation_json
from api.runners.local_docker import LocalDockerRunner
from api.models import Resource, Workspace, WorkspaceExecutedOperation, Operation

# the api/tests dir
TESTDIR = os.path.dirname(__file__)
TESTDIR = os.path.join(TESTDIR, 'operation_test_files')

class LocalDockerRunnerTester(BaseAPITestCase):

    def setUp(self):
        self.establish_clients()
        self.filepath = os.path.join(TESTDIR, 'valid_operation.json')

    def test_handles_bad_converter_gracefully(self):
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
        mock_op_data = {
            'count_matrix': {
                'converter':'api.converters.data_resource.LocalDockerSingleDataResourceConverter'
            },
            'p_val': {
                'converter':'someGarbageConverter'
            }
        }
        runner = LocalDockerRunner()
        with self.assertRaises(Exception):
            runner._map_inputs(mock_op_data, TESTDIR, inputs)

    @mock.patch('api.runners.local_docker.check_container_exit_code')
    @mock.patch('api.runners.local_docker.get_finish_datetime')
    @mock.patch('api.runners.local_docker.remove_container')
    @mock.patch('api.runners.local_docker.get_logs')
    def test_handles_job_failure(self, mock_get_logs, \
        mock_remove_container, \
        mock_get_finish_datetime, \
        mock_check_container_exit_code):
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
        mock_get_logs.return_value = 'foo'

        runner.finalize(mock_executed_op)
        mock_executed_op.save.assert_called()
        mock_remove_container.assert_called()
        self.assertTrue(mock_executed_op.job_failed)

    @mock.patch('api.runners.local_docker.check_container_exit_code')
    @mock.patch('api.runners.local_docker.get_finish_datetime')
    @mock.patch('api.runners.local_docker.remove_container')
    def test_handles_output_conversion_error(self, \
        mock_remove_container, \
        mock_get_finish_datetime, \
        mock_check_container_exit_code):
        '''
        If a job succeeds, but the outputs fail to convert
        for some reason, check that we give the user an appropriate
        message and notify the admins
        '''
        runner = LocalDockerRunner()
        mock_load_outputs_file = mock.MagicMock()
        mock_load_outputs_file.return_value = {} # doesn't matter what this is
        mock_convert_outputs = mock.MagicMock()
        mock_convert_outputs.side_effect = [OutputConversionException('!!!')]

        runner.load_outputs_file = mock_load_outputs_file
        runner.convert_outputs = mock_convert_outputs

        mock_executed_op = mock.MagicMock()
        u = str(uuid.uuid4())
        mock_executed_op.job_id = u

        mock_get_finish_datetime.return_value = datetime.datetime.now()
        mock_check_container_exit_code.return_value = 0

        runner.finalize(mock_executed_op)
        mock_executed_op.save.assert_called()
        mock_remove_container.assert_called()
        self.assertTrue(mock_executed_op.job_failed)

    @mock.patch('api.runners.local_docker.check_container_exit_code')
    @mock.patch('api.runners.local_docker.get_finish_datetime')
    @mock.patch('api.runners.local_docker.remove_container')
    @mock.patch('api.runners.local_docker.get_logs')
    @mock.patch('api.runners.local_docker.alert_admins')
    def test_handles_job_out_of_memory_error(self, \
        mock_alert_admins, \
        mock_get_logs, \
        mock_remove_container, \
        mock_get_finish_datetime, \
        mock_check_container_exit_code):
        '''
        If a Docker-based job exits due to an out-of-memory issue, Docker
        issues a 137 exit code
        '''
        runner = LocalDockerRunner()
        mock_executed_op = mock.MagicMock()
        u = str(uuid.uuid4())
        mock_executed_op.job_id = u

        mock_get_finish_datetime.return_value = datetime.datetime.now()
        mock_check_container_exit_code.return_value = 137
        mock_get_logs.return_value = 'foo'

        runner.finalize(mock_executed_op)
        mock_executed_op.save.assert_called()
        mock_remove_container.assert_called()
        self.assertTrue(mock_executed_op.job_failed)
        mock_messages = mock_executed_op.error_messages
        self.assertTrue(mock_messages[0] == 'foo')
        self.assertTrue('out of memory' in mock_messages[1])
        mock_alert_admins.assert_called()


    @mock.patch('api.runners.local_docker.check_container_exit_code')
    @mock.patch('api.runners.local_docker.get_finish_datetime')
    @mock.patch('api.runners.local_docker.remove_container')
    @mock.patch('api.runners.local_docker.get_logs')
    def test_handles_job_failure_case2(self, mock_get_logs, \
        mock_remove_container, \
        mock_get_finish_datetime, \
        mock_check_container_exit_code):
        '''
        If a job fails, the container should issue a non-zero exit code
        If that happens, test that we handle the failure appropriately and
        set the proper fields on the database object

        Here, we use an actual instance of an ExecutedOperation so we can test 
        that the save happens appropriately
        '''
        runner = LocalDockerRunner()

        # need a user's workspace to create an ExecutedOperation
        user_workspaces = Workspace.objects.filter(owner=self.regular_user_1)
        if len(user_workspaces) == 0:
            msg = '''
                Testing not setup correctly.  Please ensure that there is at least one
                Workspace for user {user}.
            '''.format(user=self.regular_user_1)
            raise ImproperlyConfigured(msg)
        workspace = user_workspaces[0]
        workspace_exec_op_uuid = uuid.uuid4()
        ops = Operation.objects.all()
        op = ops[0]
        op.workspace_operation = True
        op.save()
        workspace_exec_op = WorkspaceExecutedOperation.objects.create(
            id = workspace_exec_op_uuid,
            owner = self.regular_user_1,
            workspace= workspace,
            operation = op,
            job_id = workspace_exec_op_uuid, # does not have to be the same as the pk, but is here
            mode = 'foo'
        )

        mock_get_finish_datetime.return_value = datetime.datetime.now()
        mock_check_container_exit_code.return_value = 1
        mock_get_logs.return_value = 'ACK'

        runner.finalize(workspace_exec_op)
        mock_remove_container.assert_called()
        # query the db:
        workspace_exec_op = WorkspaceExecutedOperation.objects.get(pk=workspace_exec_op_uuid)
        self.assertTrue(workspace_exec_op.job_failed)
        self.assertTrue(workspace_exec_op.error_messages == ['ACK'])


    @mock.patch('api.runners.local_docker.alert_admins')
    @mock.patch('api.runners.local_docker.make_local_directory')
    @mock.patch('api.runners.local_docker.os.path.exists')
    @mock.patch('api.runners.local_docker.run_shell_command')
    def test_handles_container_start_failure(self, \
        mock_run_shell_command, \
        mock_os_exists, \
        mock_make_local_directory, \
        mock_alert_admins):
        '''
        If the docker container never starts, then we need to handle 
        appropriately.
        '''
        runner = LocalDockerRunner()
        mock_map_inputs = mock.MagicMock()
        mock_copy_data_resources = mock.MagicMock()
        mock_get_entrypoint_command = mock.MagicMock()
        mock_get_entrypoint_command.return_value = 'some_command'
        mock_map_inputs.return_value = {'abc':123}
        runner._map_inputs = mock_map_inputs
        runner._copy_data_resources = mock_copy_data_resources
        runner._get_entrypoint_command = mock_get_entrypoint_command

        mock_os_exists.return_value = True
        mock_run_shell_command.side_effect = Exception('!!!')

        mock_executed_op = mock.MagicMock()
        u = str(uuid.uuid4())
        mock_executed_op.job_id = u
        mock_op_data = {
            'id': 'some ID',
            'repo_name': 'name',
            'git_hash': 'abc123'
        }
        mock_inputs = {'some': 'input'}
        runner.run(mock_executed_op, mock_op_data, mock_inputs)
        mock_alert_admins.assert_called()
        mock_make_local_directory.assert_called()
        mock_run_shell_command.assert_called()
        self.assertTrue(mock_executed_op.job_failed)
        mock_executed_op.save.assert_called()

    @mock.patch('api.runners.local_docker.check_container_exit_code')
    @mock.patch('api.runners.local_docker.get_finish_datetime')
    @mock.patch('api.runners.local_docker.remove_container')
    @mock.patch('api.runners.base.get_operation_instance_data')
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
    @mock.patch('api.runners.base.get_operation_instance_data')
    @mock.patch('api.runners.local_docker.LocalDockerOutputConverter')
    @mock.patch('api.runners.base.alert_admins')
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