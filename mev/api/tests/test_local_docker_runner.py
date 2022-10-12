import unittest
import unittest.mock as mock
import os
import json
import copy
import uuid
import shutil
import datetime 
from tempfile import NamedTemporaryFile

from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from exceptions import OutputConversionException

from data_structures.operation import Operation

from api.tests.base import BaseAPITestCase
from api.runners.local_docker import LocalDockerRunner
from api.models import Resource, \
    Workspace, \
    WorkspaceExecutedOperation, \
    Operation as OperationDb

# the api/tests dir
TESTDIR = os.path.dirname(__file__)
TESTDIR = os.path.join(TESTDIR, 'operation_test_files')


class LocalDockerRunnerTester(BaseAPITestCase):

    def setUp(self):
        self.establish_clients()
        self.filepath = os.path.join(TESTDIR, 
            'valid_complete_workspace_operation.json')

    @mock.patch('api.runners.local_docker.check_container_exit_code')
    @mock.patch('api.runners.local_docker.get_finish_datetime')
    @mock.patch('api.runners.local_docker.remove_container')
    @mock.patch('api.runners.local_docker.get_logs')
    @mock.patch('api.runners.local_docker.alert_admins')
    def test_handles_job_failure(self, mock_alert_admins, \
        mock_get_logs, \
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

        runner.finalize(mock_executed_op, {})
        mock_executed_op.save.assert_called()
        mock_remove_container.assert_called()
        self.assertTrue(mock_executed_op.job_failed)
        self.assertFalse(mock_executed_op.is_finalizing)
        mock_alert_admins.assert_called()

    @mock.patch('api.runners.local_docker.check_container_exit_code')
    @mock.patch('api.runners.local_docker.get_finish_datetime')
    @mock.patch('api.runners.local_docker.remove_container')
    @mock.patch('api.runners.local_docker.alert_admins')
    def test_handles_output_conversion_error(self, \
        mock_alert_admins, \
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
        mock_convert_outputs.side_effect = OutputConversionException('!!!')

        runner.load_outputs_file = mock_load_outputs_file
        runner._convert_outputs = mock_convert_outputs

        mock_executed_op = mock.MagicMock()
        u = str(uuid.uuid4())
        mock_executed_op.job_id = u

        mock_get_finish_datetime.return_value = datetime.datetime.now()
        mock_check_container_exit_code.return_value = 0

        runner.finalize(mock_executed_op, {})
        mock_executed_op.save.assert_called()
        mock_remove_container.assert_called()
        self.assertTrue(mock_executed_op.job_failed)
        mock_alert_admins.assert_called()

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

        runner.finalize(mock_executed_op, {})
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
        ops = OperationDb.objects.all()
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

        runner.finalize(workspace_exec_op, {})
        mock_remove_container.assert_called()
        # query the db:
        workspace_exec_op = WorkspaceExecutedOperation.objects.get(pk=workspace_exec_op_uuid)
        self.assertTrue(workspace_exec_op.job_failed)
        self.assertTrue(workspace_exec_op.error_messages == ['ACK'])


    @mock.patch('api.runners.local_docker.alert_admins')
    @mock.patch('api.runners.local_docker.make_local_directory')
    @mock.patch('api.runners.local_docker.os.path.exists')
    @mock.patch('api.runners.local_docker.run_shell_command')
    @mock.patch('api.runners.local_docker.get_image_name_and_tag')
    def test_handles_container_start_failure(self, \
        mock_get_image_name_and_tag, \
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
        mock_get_image_name_and_tag.return_value = ''
        runner._convert_inputs = mock_map_inputs
        runner._copy_data_resources = mock_copy_data_resources
        runner._get_entrypoint_command = mock_get_entrypoint_command

        mock_os_exists.return_value = True
        mock_run_shell_command.side_effect = Exception('!!!')

        mock_executed_op = mock.MagicMock()
        u = str(uuid.uuid4())
        mock_executed_op.job_id = u
        op = Operation(json.load(open(self.filepath)))
        mock_inputs = {'some': 'input'}
        runner.run(mock_executed_op, op, mock_inputs)
        mock_alert_admins.assert_called()
        mock_make_local_directory.assert_called()
        mock_run_shell_command.assert_called()
        self.assertTrue(mock_executed_op.job_failed)
        mock_executed_op.save.assert_called()

    @mock.patch('api.runners.local_docker.check_container_exit_code')
    @mock.patch('api.runners.local_docker.get_finish_datetime')
    @mock.patch('api.runners.local_docker.remove_container')
    def test_handles_job_finalization(self, \
        mock_remove_container, \
        mock_get_finish_datetime, \
        mock_check_container_exit_code):
        '''
        If a job succeeds, check that we call all the right functions
        '''
        runner = LocalDockerRunner()
        mock_load_outputs = mock.MagicMock()
        mock_outputs = {'abc': 123}
        mock_load_outputs.return_value = mock_outputs
        runner.load_outputs_file = mock_load_outputs

        mock_convert_outputs = mock.MagicMock()
        mock_convert_outputs.return_value = {
            'abc': 246 # the "conversion" doubled the number
        }
        runner._convert_outputs = mock_convert_outputs

        mock_op = mock.MagicMock()

        mock_executed_op = mock.MagicMock()
        u = str(uuid.uuid4())
        mock_executed_op.job_id = u
        mock_workspace = mock.MagicMock()
        mock_executed_op.workspace = mock_workspace

        mock_get_finish_datetime.return_value = datetime.datetime.now()
        mock_check_container_exit_code.return_value = 0

        runner.finalize(mock_executed_op, mock_op)

        mock_convert_outputs.assert_called_once_with(
            mock_executed_op, mock_op, mock_outputs
        )
        mock_executed_op.save.assert_called()
        mock_remove_container.assert_called()
        self.assertFalse(mock_executed_op.job_failed)
        self.assertFalse(mock_executed_op.is_finalizing)
        self.assertDictEqual(mock_executed_op.outputs,{'abc': 246})

    def test_entrypoint_command_creation(self):
        '''
        Tests that we create the entrypoint command
        from the template as expected
        '''
        input_path = '/home/xyz/input.tsv'
        a_arg = 10
        cmd = b'Rscript something.R {{input_file}} -a {{a_arg}}'
        expected_cmd = 'Rscript something.R ' + \
            input_path + ' -a ' + str(a_arg)
        runner = LocalDockerRunner()
        with NamedTemporaryFile() as tf:
            tf.write(cmd)
            tf.seek(0)
            fname = tf.name
            arg_dict = {
                'a_arg': a_arg,
                'input_file': input_path
            }
            final_cmd = runner._get_entrypoint_command(fname, arg_dict)
            self.assertEqual(final_cmd, expected_cmd)

    @override_settings(OPERATION_LIBRARY_DIR='/data/op_dir')
    @override_settings(OPERATION_EXECUTION_DIR='/data/ex_dir')
    @mock.patch('api.runners.local_docker.run_shell_command')
    @mock.patch('api.runners.local_docker.get_image_name_and_tag')
    @mock.patch('api.runners.local_docker.make_local_directory')
    @mock.patch('api.runners.local_docker.os.path.exists')
    def test_run_initiation(self, \
        mock_exists, \
        mock_make_local_directory, \
        mock_get_image_name_and_tag, \
        mock_run_shell_command):

        mock_exists.return_value = True
        mock_image_name = 'docker.io/foo:bar'
        mock_get_image_name_and_tag.return_value = mock_image_name

        runner = LocalDockerRunner()
        mock_convert_inputs = mock.MagicMock()
        mock_convert_inputs.return_value = {}
        mock_entrypoint_cmd = mock.MagicMock()
        mock_cmd = 'Rscript something.R'
        mock_entrypoint_cmd.return_value = mock_cmd
        runner._convert_inputs = mock_convert_inputs
        runner._get_entrypoint_command = mock_entrypoint_cmd

        op = Operation(json.load(open(self.filepath)))
        validated_inputs = {'abc': 1}
        mock_executed_op = mock.MagicMock()
        u = uuid.uuid4()
        mock_executed_op.id = u

        runner.run(mock_executed_op, op, validated_inputs)
        mock_op_dir = f'/data/op_dir/{op.id}'
        mock_ex_dir = f'/data/ex_dir/{u}'
        mock_make_local_directory.assert_called_once_with(mock_ex_dir)
        mock_convert_inputs.assert_called_once_with(
            op,
            mock_op_dir,
            validated_inputs,
            mock_ex_dir
        )
        expected_docker_cmd = LocalDockerRunner.DOCKER_RUN_CMD.format(
            container_name = str(u),
            execution_mount = '/data/ex_dir',
            work_dir = '/data/ex_dir',
            job_dir = mock_ex_dir,
            docker_image = mock_image_name,
            cmd = mock_cmd
        )
        mock_run_shell_command.assert_called_once_with(expected_docker_cmd)
    
    @mock.patch('api.runners.local_docker.delete_resource_by_pk')
    def test_cleanup_on_error(self, mock_delete):
        op = Operation(json.load(open(self.filepath)))
        runner = LocalDockerRunner()
        u1 = str(uuid.uuid4())
        u2 = str(uuid.uuid4())
        mock_outputs = {
            'norm_counts': u1,
            'dge_table': u2
        }
        runner.cleanup_on_error(op.outputs, mock_outputs)
        mock_delete.assert_has_calls([
            mock.call(u1),
            mock.call(u2)
        ])    

