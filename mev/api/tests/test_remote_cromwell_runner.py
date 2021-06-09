import unittest
import unittest.mock as mock
import os
import uuid
import datetime

from django.core.exceptions import ImproperlyConfigured

from api.tests.base import BaseAPITestCase
from api.utilities.operations import read_operation_json
from api.runners.remote_cromwell import RemoteCromwellRunner
from api.models.operation import Operation
from api.models.executed_operation import ExecutedOperation
from api.models.workspace_executed_operation import WorkspaceExecutedOperation
from api.models.workspace import Workspace

# the api/tests dir
TESTDIR = os.path.dirname(__file__)
TESTDIR = os.path.join(TESTDIR, 'operation_test_files', 'demo_cromwell_workflow')

class RemoteCromwellRunnerTester(BaseAPITestCase):

    def setUp(self):
        self.establish_clients()

        os.environ['CROMWELL_SERVER_URL'] = 'http://mock-cromwell-server:8080'
        os.environ['CROMWELL_BUCKET'] = 'my-bucket'

        # create a ExecutedOperation to work with:
        ops = Operation.objects.all()
        if len(ops) == 0:
            raise ImproperlyConfigured('Need at least one Operation to run this test.')
        op = ops[0]
        workspaces = Workspace.objects.all()
        if len(workspaces) == 0:
            raise ImproperlyConfigured('Need at least one Workspace to run this test.')
        workspace = workspaces[0]
        workspace_exec_op_pk = uuid.uuid4()
        job_name = 'foo'
        self.workspace_executed_op = WorkspaceExecutedOperation.objects.create(
            id=workspace_exec_op_pk,
            owner = self.regular_user_1,
            workspace=workspace,
            job_name = job_name,
            inputs = {},
            operation = op,
            mode = 'cromwell',
            status = WorkspaceExecutedOperation.SUBMITTED
        )

        exec_op_pk = uuid.uuid4()
        job_name = 'bar'
        self.executed_op = ExecutedOperation.objects.create(
            id=exec_op_pk,
            owner = self.regular_user_1,
            job_name = job_name,
            inputs = {},
            operation = op,
            mode = 'cromwell',
            status = ExecutedOperation.SUBMITTED
        )

    @mock.patch('api.runners.remote_cromwell.get_docker_images_in_repo')
    @mock.patch('api.runners.remote_cromwell.build_docker_image')
    @mock.patch('api.runners.remote_cromwell.login_to_dockerhub')
    @mock.patch('api.runners.remote_cromwell.push_image_to_dockerhub')
    @mock.patch('api.runners.remote_cromwell.edit_runtime_containers')
    @mock.patch('api.runners.remote_cromwell.os.path.exists')
    def test_preparation_case1(self, mock_path_exists,
        mock_edit_runtime_containers,
        mock_push_image_to_dockerhub, 
        mock_login_to_dockerhub,
        mock_build_docker_image,
        mock_get_docker_images_in_repo
    ):
        '''
        Tests that the proper calls are made when ingesting a workflow 
        intended to run via a remote Cromwell call.
        '''
        mock_get_docker_images_in_repo.return_value = [
            'docker.io/myUser/foo:tagA',
            'docker.io/myUser/bar:tagB',
        ]
        git_hash = 'abc123'
        mock_path_exists.side_effect = [True, True]
        mock_push_image_to_dockerhub.side_effect = [
            'docker.io/mevUser/foo:%s' % git_hash,
            'docker.io/mevUser/bar:%s' % git_hash
        ]

        expected_name_mapping = {
            'docker.io/myUser/foo:tagA': 'docker.io/mevUser/foo:%s' % git_hash,
            'docker.io/myUser/bar:tagB': 'docker.io/mevUser/bar:%s' % git_hash
        }

        # call the tested function:
        rcr = RemoteCromwellRunner()
        mock_op_dir = '/abc/'
        rcr.prepare_operation(mock_op_dir, 'some-repo', git_hash)

        self.assertEqual(mock_build_docker_image.call_count, 2)
        mock_login_to_dockerhub.assert_called()
        self.assertEqual(mock_push_image_to_dockerhub.call_count, 2)
        mock_edit_runtime_containers.assert_called_with(mock_op_dir, expected_name_mapping)

    @mock.patch('api.runners.remote_cromwell.get_docker_images_in_repo')
    @mock.patch('api.runners.remote_cromwell.build_docker_image')
    @mock.patch('api.runners.remote_cromwell.login_to_dockerhub')
    @mock.patch('api.runners.remote_cromwell.push_image_to_dockerhub')
    @mock.patch('api.runners.remote_cromwell.edit_runtime_containers')
    @mock.patch('api.runners.remote_cromwell.os.path.exists')
    def test_preparation_case2(self, mock_path_exists,
        mock_edit_runtime_containers,
        mock_push_image_to_dockerhub, 
        mock_login_to_dockerhub,
        mock_build_docker_image,
        mock_get_docker_images_in_repo
    ):
        '''
        Tests that the proper calls are made when ingesting a workflow 
        intended to run via a remote Cromwell call.

        Here, we use docker images that do NOT have the docker.io repo prefix
        '''
        mock_get_docker_images_in_repo.return_value = [
            'myUser/foo:tagA',
            'myUser/bar',
        ]
        git_hash = 'abc123'
        mock_path_exists.side_effect = [True, True]
        mock_push_image_to_dockerhub.side_effect = [
            'docker.io/mevUser/foo:%s' % git_hash,
            'docker.io/mevUser/bar:%s' % git_hash
        ]

        expected_name_mapping = {
            'myUser/foo:tagA': 'docker.io/mevUser/foo:%s' % git_hash,
            'myUser/bar': 'docker.io/mevUser/bar:%s' % git_hash
        }

        # call the tested function:
        rcr = RemoteCromwellRunner()
        mock_op_dir = '/abc/'
        rcr.prepare_operation(mock_op_dir, 'some-repo', git_hash)

        self.assertEqual(mock_build_docker_image.call_count, 2)
        mock_login_to_dockerhub.assert_called()
        self.assertEqual(mock_push_image_to_dockerhub.call_count, 2)
        mock_edit_runtime_containers.assert_called_with(mock_op_dir, expected_name_mapping)



    @mock.patch('api.runners.remote_cromwell.datetime')
    @mock.patch('api.runners.remote_cromwell.alert_admins')
    def test_handle_submission(self, mock_alert_admins, mock_datetime):
        '''
        Tests the behavior after we POST to the Cromwell server when 
        submitting a new job
        '''

        mock_response = mock.MagicMock()
        u = uuid.uuid4()
        mock_response.text = '{"id":"' + str(u) + '", "status":"' + RemoteCromwellRunner.SUBMITTED_STATUS + '"}'
        mock_response.status_code = 201
        now = datetime.datetime.now()
        mock_datetime.datetime.now.return_value = now

        rcr = RemoteCromwellRunner()
        rcr.handle_submission_response(mock_response, self.executed_op)
        self.assertEqual(self.executed_op.job_id, str(u))
        self.assertEqual(self.executed_op.execution_start_datetime, now)

        mock_response.status_code = 400
        rcr.handle_submission_response(mock_response, self.executed_op)
        mock_alert_admins.assert_called()

    def test_handle_job_check(self):
        '''
        Tests the 'check status' method for the remote cromwell runners.
        '''
        u = uuid.uuid4()
        rcr = RemoteCromwellRunner()
        mock_query_for_status = mock.MagicMock()
        mock_query_for_status.return_value = {'status': RemoteCromwellRunner.SUCCEEDED_STATUS}
        rcr.query_for_status = mock_query_for_status
        result = rcr.check_status(u)
        self.assertTrue(result)

        mock_query_for_status = mock.MagicMock()
        mock_query_for_status.return_value = {'status': RemoteCromwellRunner.FAILED_STATUS}
        rcr.query_for_status = mock_query_for_status
        result = rcr.check_status(u)
        self.assertTrue(result) # failed is technically complete, so we get True back

        mock_query_for_status = mock.MagicMock()
        mock_query_for_status.return_value = {'status': RemoteCromwellRunner.OTHER_STATUS}
        rcr.query_for_status = mock_query_for_status
        result = rcr.check_status(u)
        self.assertFalse(result)

    @mock.patch('api.runners.remote_cromwell.get_with_retry')
    def test_handle_job_check_with_query(self, mock_get):
        '''
        Tests the 'check status' method for the remote cromwell runners. 
        This version mocks the get call to Cromwell.
        '''
        u = uuid.uuid4()
        rcr = RemoteCromwellRunner()
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"status":"'+ RemoteCromwellRunner.SUCCEEDED_STATUS +'"}'
        mock_get.return_value = mock_response
        result = rcr.check_status(u)
        self.assertTrue(result)

        mock_response = mock.MagicMock()
        mock_response.status_code = 400
        mock_response.text = '{"status":"junk status"}'
        mock_get.return_value = mock_response
        result = rcr.check_status(u)
        self.assertFalse(result)

    @mock.patch('api.runners.remote_cromwell.RemoteCromwellRunner.query_for_metadata')
    @mock.patch('api.runners.remote_cromwell.RemoteCromwellRunner.convert_outputs')
    @mock.patch('api.runners.remote_cromwell.RemoteCromwellRunner.query_for_status')
    @mock.patch('api.runners.remote_cromwell.RemoteCromwellRunner._parse_status_response')
    def test_job_success(self, mock_parse_status_response, 
        mock_query_for_status,  
        mock_convert_outputs, 
        mock_query_for_metadata):
        '''
        Tests that the expected things happen when we call the `handle_job_success`
        following completion of a job.
        '''
        # just have it 'return' something not None
        mock_query_for_status.return_value = {'x': 1}
        mock_parse_status_response.return_value = RemoteCromwellRunner.SUCCEEDED_STATUS

        mock_convert_outputs.return_value = {'a':1}
        mock_job_metadata = {
            'end': '2020-10-28T00:05:03.694Z',
            'outputs': {'a':'1'} # pretend the original input was a number, represented as a string
        }
        expected_end_datetime = datetime.datetime(2020, 10, 28, 
            hour=0, minute=5, second=3, microsecond=694000)
        mock_query_for_metadata.return_value = mock_job_metadata

        # query the ExecutedOp 
        exec_op_id = self.executed_op.id
        exec_op = ExecutedOperation.objects.get(id=exec_op_id)
        self.assertIsNone(exec_op.outputs)
        self.assertFalse(exec_op.job_failed)
        self.assertIsNone(exec_op.execution_stop_datetime)

        # call the tested func.
        rcr = RemoteCromwellRunner()
        rcr.finalize(self.executed_op)

        # query again to see changes were made to the db
        exec_op = ExecutedOperation.objects.get(id=exec_op_id)
        self.assertDictEqual(exec_op.outputs, {'a':1})
        self.assertFalse(exec_op.job_failed)
        dt_w_tzinfo = exec_op.execution_stop_datetime
        dt_wout_tzinfo = dt_w_tzinfo.replace(tzinfo=None)
        self.assertEqual(dt_wout_tzinfo, expected_end_datetime)

    @mock.patch('api.runners.remote_cromwell.RemoteCromwellRunner.query_for_metadata')
    @mock.patch('api.runners.remote_cromwell.alert_admins')
    @mock.patch('api.runners.remote_cromwell.RemoteCromwellRunner.query_for_status')
    @mock.patch('api.runners.remote_cromwell.RemoteCromwellRunner._parse_status_response')
    def test_job_success_with_missing_outputs(self, mock_parse_status_response, 
        mock_query_for_status, 
        mock_alert_admins, 
        mock_query_for_metadata):
        '''
        Tests that the expected things happen when we call the `handle_job_success`
        following completion of a job. Here, we mock there being no outputs key 
        in the returned metadata payload
        '''
        # just have it 'return' something not None
        mock_query_for_status.return_value = {'x': 1}
        mock_parse_status_response.return_value = RemoteCromwellRunner.SUCCEEDED_STATUS

        mock_job_metadata = {
            'end': '2020-10-28T00:05:03.694Z'
        }
        expected_end_datetime = datetime.datetime(2020, 10, 28, 
            hour=0, minute=5, second=3, microsecond=694000)
        mock_query_for_metadata.return_value = mock_job_metadata

        # query the ExecutedOp 
        exec_op_id = self.executed_op.id
        exec_op = ExecutedOperation.objects.get(id=exec_op_id)
        self.assertIsNone(exec_op.outputs)
        self.assertFalse(exec_op.job_failed)
        self.assertIsNone(exec_op.execution_stop_datetime)

        # call the tested function
        rcr = RemoteCromwellRunner()
        mock_convert_outputs = mock.MagicMock()
        mock_convert_outputs.return_value = {}
        rcr.convert_outputs = mock_convert_outputs
        rcr.finalize(self.executed_op)

        # query again to see changes were made to the db
        exec_op = ExecutedOperation.objects.get(id=exec_op_id)
        self.assertDictEqual(exec_op.outputs, {})
        self.assertFalse(exec_op.job_failed)
        dt_w_tzinfo = exec_op.execution_stop_datetime
        dt_wout_tzinfo = dt_w_tzinfo.replace(tzinfo=None)
        self.assertEqual(dt_wout_tzinfo, expected_end_datetime)

        mock_alert_admins.assert_called()

    @mock.patch('api.runners.remote_cromwell.RemoteCromwellRunner.query_for_metadata')
    @mock.patch('api.runners.remote_cromwell.RemoteCromwellRunner.convert_outputs')
    @mock.patch('api.runners.remote_cromwell.RemoteCromwellRunner.query_for_status')
    @mock.patch('api.runners.remote_cromwell.RemoteCromwellRunner._parse_status_response')
    def test_job_failure(self, mock_parse_status_response, 
        mock_query_for_status, 
        mock_convert_outputs, 
        mock_query_for_metadata):
        '''
        Tests that the expected things happen when we call the `handle_job_failure`
        following completion of a job that failed
        '''
        # just have it 'return' something not None
        mock_query_for_status.return_value = {'x': 1}
        mock_parse_status_response.return_value = RemoteCromwellRunner.FAILED_STATUS

        mock_fail = [
            {
                'message': 'Workflow input processing failed', 
                'causedBy': [
                    {
                        'message': 'Unrecognized token on line 168, column 12:\n\n        mv ${sample_name}.trimmed_1P.fastq.gz ${sample_name}_R1.fastq.gz\n           ^', 
                        'causedBy': []
                    }
                ]
            },
            {
                'message': 'Something bad', 
                'causedBy': []
            }
        ]
        mock_job_metadata = {
            'end': '2020-10-28T00:05:03.694Z',
            'failures': mock_fail
        }
        expected_end_datetime = datetime.datetime(2020, 10, 28, 
            hour=0, minute=5, second=3, microsecond=694000)
        mock_query_for_metadata.return_value = mock_job_metadata

        # query the ExecutedOp 
        exec_op_id = self.executed_op.id
        exec_op = ExecutedOperation.objects.get(id=exec_op_id)
        self.assertIsNone(exec_op.outputs)
        self.assertFalse(exec_op.job_failed)
        self.assertIsNone(exec_op.execution_stop_datetime)

        # call the tested func.
        rcr = RemoteCromwellRunner()
        rcr.finalize(self.executed_op)

        # query again to see changes were made to the db
        exec_op = ExecutedOperation.objects.get(id=exec_op_id)
        self.assertIsNone(exec_op.outputs)
        self.assertTrue(exec_op.job_failed) # DID fail
        dt_w_tzinfo = exec_op.execution_stop_datetime
        dt_wout_tzinfo = dt_w_tzinfo.replace(tzinfo=None)
        self.assertEqual(dt_wout_tzinfo, expected_end_datetime)
        error_messages = exec_op.error_messages
        self.assertCountEqual(
            error_messages, 
            ['Workflow input processing failed', 'Something bad']
        )

    @mock.patch('api.runners.remote_cromwell.RemoteCromwellRunner.handle_job_success')
    @mock.patch('api.runners.remote_cromwell.RemoteCromwellRunner.handle_job_failure')
    @mock.patch('api.runners.remote_cromwell.RemoteCromwellRunner.handle_other_job_outcome')
    @mock.patch('api.runners.remote_cromwell.RemoteCromwellRunner.query_for_status')
    def test_job_status_options(self, mock_query_for_status,
        mock_handle_other_job_outcome,
        mock_handle_job_failure,
        mock_handle_job_success
    ):
        '''
        Tests that we hit the proper 'finalization' methods depending on the response 
        from the Cromwell server
        '''
        rcr = RemoteCromwellRunner()

        mock_query_for_status.return_value = {
            'id': 'abc',
            'status': RemoteCromwellRunner.SUCCEEDED_STATUS
        }
        rcr.finalize(self.executed_op)
        mock_handle_job_success.assert_called()
        mock_handle_job_failure.assert_not_called()
        mock_handle_other_job_outcome.assert_not_called()

        # reset the mocks
        mock_handle_job_success.reset_mock()
        mock_handle_job_failure.reset_mock()
        mock_handle_other_job_outcome.reset_mock()

        # mock a failure response
        mock_query_for_status.return_value = {
            'id': 'abc',
            'status': RemoteCromwellRunner.FAILED_STATUS
        }
        rcr.finalize(self.executed_op)
        mock_handle_job_success.assert_not_called()
        mock_handle_job_failure.assert_called()
        mock_handle_other_job_outcome.assert_not_called()
        mock_handle_job_success.reset_mock()
        mock_handle_job_failure.reset_mock()
        mock_handle_other_job_outcome.reset_mock()

        mock_query_for_status.return_value = {
            'id': 'abc',
            'status': 'XYZ'
        }
        rcr.finalize(self.executed_op)
        mock_handle_other_job_outcome.assert_called()
        mock_handle_job_success.assert_not_called()
        mock_handle_job_failure.assert_not_called()