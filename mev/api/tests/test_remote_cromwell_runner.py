import unittest
import unittest.mock as mock
import os
import uuid
import datetime

from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from exceptions import OutputConversionException, \
    JobSubmissionException

from api.tests.base import BaseAPITestCase
from api.runners.remote_cromwell import RemoteCromwellRunner
from api.models.operation import Operation
from api.models.executed_operation import ExecutedOperation
from api.models.workspace_executed_operation import WorkspaceExecutedOperation
from api.models.workspace import Workspace

# the api/tests dir
TESTDIR = os.path.dirname(__file__)
TESTDIR = os.path.join(TESTDIR, 'operation_test_files', 'demo_cromwell_workflow')


@override_settings(CROMWELL_SERVER_URL='http://mock-cromwell-server:8080')
@override_settings(CROMWELL_BUCKET_NAME='my-bucket')
class RemoteCromwellRunnerTester(BaseAPITestCase):

    def setUp(self):
        self.establish_clients()

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

    @mock.patch('api.runners.remote_cromwell.get_tag_format')
    @mock.patch('api.runners.remote_cromwell.get_docker_images_in_repo')
    @mock.patch('api.runners.remote_cromwell.check_image_exists')
    @mock.patch('api.runners.remote_cromwell.edit_runtime_containers')
    def test_preparation_case1(self,
        mock_edit_runtime_containers,
        mock_check_image_exists, 
        mock_get_docker_images_in_repo,
        mock_get_tag_format
    ):
        '''
        Tests that the proper calls are made when ingesting a workflow 
        intended to run via a remote Cromwell call.

        Here, we test that a tag is added to the Docker image associated
        with the repo and that the "external" docker image (bar:tagB)
        is untouched.
        '''
        # here, mock that one of the Docker images is associated with 
        # the repo (e.g. it has the same name as the repo). The second
        # is 'external', e.g. like a samtools Docker could be.
        mock_get_docker_images_in_repo.return_value = [
            'docker.io/myUser/my-repo',
            'docker.io/myUser/bar:tagB',
        ]
        git_hash = 'abc123'
        mock_check_image_exists.side_effect = [True, True]
        mock_get_tag_format.return_value = '{hash}'

        expected_name_mapping = {
            'docker.io/myUser/my-repo': 'docker.io/myUser/my-repo:%s' % git_hash,
            'docker.io/myUser/bar:tagB': 'docker.io/myUser/bar:tagB'
        }

        # call the tested function:
        rcr = RemoteCromwellRunner()
        mock_op_dir = '/abc/'
        rcr.prepare_operation(mock_op_dir, 'my-repo', git_hash)

        self.assertEqual(mock_check_image_exists.call_count, 2)
        mock_edit_runtime_containers.assert_called_with(mock_op_dir, expected_name_mapping)

    @mock.patch('api.runners.remote_cromwell.get_docker_images_in_repo')
    def test_preparation_case2(self, mock_get_docker_images_in_repo):
        '''
        Tests that the proper calls are made when ingesting a workflow 
        intended to run via a remote Cromwell call.

        Here, we test that a failure to specify the docker repo raises
        an exception. We can't guess that they'll come from Dockerhub, GCR, etc.
        '''
        # here, mock that the Docker image does not have the registry prefix
        # which is invalid as far as we are concerned
        mock_get_docker_images_in_repo.return_value = [
            'myUser/my-repo',
        ]

        # call the tested function:
        rcr = RemoteCromwellRunner()
        mock_op_dir = '/abc/'
        with self.assertRaisesRegex(Exception, 'did not correspond to any docker registry we are aware of'):
            rcr.prepare_operation(mock_op_dir, 'my-repo', '')

    @mock.patch('api.runners.remote_cromwell.get_docker_images_in_repo')
    def test_preparation_case3(self, mock_get_docker_images_in_repo):
        '''
        Tests that the proper calls are made when ingesting a workflow 
        intended to run via a remote Cromwell call.

        Here, we test that a failure to specify the docker repo raises
        an exception. We can't guess that they'll come from Dockerhub, GCR, etc.
        '''
        # here, mock that the image string is malformatted (e.g. two colons)
        mock_get_docker_images_in_repo.return_value = [
            'ghcr.io/myUser/my-repo:a:b',
        ]

        # call the tested function:
        rcr = RemoteCromwellRunner()
        mock_op_dir = '/abc/'
        with self.assertRaisesRegex(Exception, 'image handle'):
            rcr.prepare_operation(mock_op_dir, 'my-repo', '')


    @mock.patch('api.runners.remote_cromwell.get_docker_images_in_repo')
    @mock.patch('api.runners.remote_cromwell.check_image_exists')
    def test_preparation_case4(self, \
        mock_check_image_exists, \
        mock_get_docker_images_in_repo):
        '''
        Tests that the proper calls are made when ingesting a workflow 
        intended to run via a remote Cromwell call.

        Here, we test the situation where we are using a docker image that
        does not contain a "username". Examples like this include basic/canned
        Docker images like docker.io/ubuntu:bionic
        '''
        # here, mock that the image string is malformatted (e.g. is missing
        # the account/user ID)
        image_name = 'docker.io/ubuntu:bionic'
        mock_get_docker_images_in_repo.return_value = [
            image_name,
        ]

        # call the tested function:
        rcr = RemoteCromwellRunner()
        mock_op_dir = '/abc/'
        rcr.prepare_operation(mock_op_dir, 'my-repo', '')
        mock_check_image_exists.assert_called_with(image_name)

    @mock.patch('api.runners.remote_cromwell.get_docker_images_in_repo')
    @mock.patch('api.runners.remote_cromwell.check_image_exists')
    @mock.patch('api.runners.remote_cromwell.edit_runtime_containers')
    def test_preparation_case5(self,
        mock_edit_runtime_containers,
        mock_check_image_exists, 
        mock_get_docker_images_in_repo
    ):
        '''
        Tests that the proper calls are made when ingesting a workflow 
        intended to run via a remote Cromwell call.

        Here, we test that an "external" image is not tagged. That is,
        the Docker image is not originating from our repository and hence
        requires a tag to be unambiguous
        '''
        # here, mock that the Docker image is 'external', e.g. 
        # like a samtools Docker could be.
        mock_get_docker_images_in_repo.return_value = [
            'docker.io/myUser/foo',
        ]

        # call the tested function:
        rcr = RemoteCromwellRunner()
        mock_op_dir = '/abc/'
        with self.assertRaisesRegex(Exception, 'require a tag'):
            rcr.prepare_operation(mock_op_dir, 'my-repo', '')

    @mock.patch('api.runners.remote_cromwell.get_tag_format')
    @mock.patch('api.runners.remote_cromwell.get_docker_images_in_repo')
    @mock.patch('api.runners.remote_cromwell.check_image_exists')
    @mock.patch('api.runners.remote_cromwell.edit_runtime_containers')
    def test_preparation_case6(self,
        mock_edit_runtime_containers,
        mock_check_image_exists, 
        mock_get_docker_images_in_repo,
        mock_get_tag_format
    ):
        '''
        Tests that the proper calls are made when ingesting a workflow 
        intended to run via a remote Cromwell call.

        Here, we test that an image cannot be located and that we fail accordingly
        '''
        # here, mock that one of the Docker images is associated with 
        # the repo (e.g. it has the same name as the repo). The second
        # is 'external', e.g. like a samtools Docker could be.
        mock_get_docker_images_in_repo.return_value = [
            'docker.io/myUser/my-repo',
            'docker.io/myUser/bar:tagB',
        ]
        git_hash = 'abc123'
        mock_check_image_exists.side_effect = [True, False]
        mock_get_tag_format.return_value = '{hash}'

        # call the tested function:
        rcr = RemoteCromwellRunner()
        mock_op_dir = '/abc/'
        with self.assertRaisesRegex(Exception, 'Could not locate'):
            rcr.prepare_operation(mock_op_dir, 'my-repo', git_hash)

        self.assertEqual(mock_check_image_exists.call_count, 2)
        mock_edit_runtime_containers.assert_not_called()

    @override_settings(CROMWELL_SERVER_URL='http://mock-cromwell-server:8080')
    @mock.patch('api.runners.remote_cromwell.post_with_retry')
    def test_send_job(self, mock_post_with_retry):
        '''
        This tests that we call the function to POST to cromwell.
        Note that we just check it's called, not the args it's called
        with (since that involves multiple open calls, etc.)

        Also tests when the post_with_retry raises an exception
        '''
        mock_response = mock.MagicMock()
        mock_post_with_retry.return_value = mock_response
        rcr = RemoteCromwellRunner()
        mock_handle_submission_response = mock.MagicMock()
        rcr.handle_submission_response = mock_handle_submission_response
        rcr.send_job(TESTDIR, self.executed_op)

        mock_post_with_retry.assert_called()
        mock_handle_submission_response.assert_called_once_with(
            mock_response,
            self.executed_op
        )

        # now try with an exception raised:
        mock_post_with_retry.reset_mock()
        mock_handle_submission_response.reset_mock()
        mock_post_with_retry.side_effect = Exception('!!!')
        rcr.send_job(TESTDIR, self.executed_op)
        mock_handle_submission_response.assert_called_once_with(
            None,
            self.executed_op
        )

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

        mock_handle_submission_issue = mock.MagicMock()
        rcr = RemoteCromwellRunner()
        rcr._handle_submission_issue = mock_handle_submission_issue

        # test a 201 response with an expected resposne payload
        rcr.handle_submission_response(mock_response, self.executed_op)
        self.assertEqual(self.executed_op.job_id, str(u))
        self.assertEqual(self.executed_op.execution_start_datetime, now)

        # test a 201 response with an unexpected payload
        mock_response.text = '{"id":"' + str(u) + '", "status":"xyz"}'
        mock_handle_submission_issue.reset_mock()
        rcr.handle_submission_response(mock_response, self.executed_op)
        mock_handle_submission_issue.assert_called_once_with(self.executed_op)

        # mock a 400 response
        mock_response.status_code = 400
        mock_handle_submission_issue.reset_mock()
        rcr.handle_submission_response(mock_response, self.executed_op)
        mock_handle_submission_issue.assert_called_once_with(self.executed_op)

        # if the POST fails, we set the response to None. Check that
        # the method handles that appropriately.
        mock_handle_submission_issue.reset_mock()
        rcr.handle_submission_response(None, self.executed_op)
        mock_handle_submission_issue.assert_called_once_with(self.executed_op)

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
    @mock.patch('api.runners.remote_cromwell.RemoteCromwellRunner.query_for_status')
    @mock.patch('api.runners.remote_cromwell.RemoteCromwellRunner._parse_status_response')
    def test_job_success(self, mock_parse_status_response, 
        mock_query_for_status,  
        mock_query_for_metadata):
        '''
        Tests that the expected things happen when we call the `handle_job_success`
        following completion of a job.
        '''
        # just have it 'return' something not None
        mock_query_for_status.return_value = {'x': 1}
        mock_parse_status_response.return_value = RemoteCromwellRunner.SUCCEEDED_STATUS

        mock_job_outputs = {'a':'1'}
        mock_job_metadata = {
            'end': '2020-10-28T00:05:03.694Z',
            'outputs': mock_job_outputs
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
        mock_op = mock.MagicMock()
        mock_convert_outputs = mock.MagicMock()
        # we "convert" by turning '1' into 2
        mock_convert_outputs.return_value = {'a':2}
        rcr._convert_outputs = mock_convert_outputs
        mock_clean_following_success = mock.MagicMock()
        rcr._clean_following_success = mock_clean_following_success
        rcr.finalize(self.executed_op, mock_op)

        # query again to see changes were made to the db
        exec_op = ExecutedOperation.objects.get(id=exec_op_id)
        self.assertDictEqual(exec_op.outputs, {'a':2})
        self.assertFalse(exec_op.job_failed)
        dt_w_tzinfo = exec_op.execution_stop_datetime
        dt_wout_tzinfo = dt_w_tzinfo.replace(tzinfo=None)
        self.assertEqual(dt_wout_tzinfo, expected_end_datetime)

        mock_convert_outputs.assert_called_once_with(
            self.executed_op,
            mock_op,
            mock_job_outputs
        )
        mock_clean_following_success.assert_called_once_with(str(exec_op_id))


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
        mock_op = mock.MagicMock()
        # this mocks the usual 
        # data_structures.operation_input_output_dict.OperationOutputDict
        # that a true Operation would have. This does, however,
        # trigger an output conversion error since we were missing
        # the outputs in the Cromwell job metadata
        mock_op.outputs = {'a': 1}

        mock_clean_following_success = mock.MagicMock()
        rcr._clean_following_success = mock_clean_following_success

        # call the tested function. Note that while the 
        # _convert_outputs method raises an OutputConversionException,
        # we catch that in handle_job_success, marking the 
        # appropriate database fields
        rcr.finalize(self.executed_op, mock_op)

        # query again to see changes were made to the db
        exec_op = ExecutedOperation.objects.get(id=exec_op_id)
        self.assertIsNone(exec_op.outputs)
        self.assertTrue(exec_op.job_failed)
        dt_w_tzinfo = exec_op.execution_stop_datetime
        dt_wout_tzinfo = dt_w_tzinfo.replace(tzinfo=None)
        self.assertEqual(dt_wout_tzinfo, expected_end_datetime)
        self.assertEqual(exec_op.status, ExecutedOperation.FINALIZING_ERROR)
        mock_alert_admins.assert_called()
        mock_clean_following_success.assert_not_called()

    @mock.patch('api.runners.remote_cromwell.RemoteCromwellRunner.query_for_metadata')
    @mock.patch('api.runners.remote_cromwell.RemoteCromwellRunner.query_for_status')
    @mock.patch('api.runners.remote_cromwell.RemoteCromwellRunner._parse_status_response')
    def test_job_failure(self, mock_parse_status_response, 
        mock_query_for_status, 
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
        mock_op = mock.MagicMock()
        mock_clean_following_success = mock.MagicMock()
        rcr._clean_following_success = mock_clean_following_success
        rcr.finalize(self.executed_op, mock_op)

        mock_clean_following_success.assert_not_called()

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
        rcr.finalize(self.executed_op,{})
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
        rcr.finalize(self.executed_op,{})
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
        rcr.finalize(self.executed_op,{})
        mock_handle_other_job_outcome.assert_called()
        mock_handle_job_success.assert_not_called()
        mock_handle_job_failure.assert_not_called()

    @mock.patch('api.runners.remote_cromwell.RemoteCromwellRunner.query_for_metadata')
    @mock.patch('api.runners.remote_cromwell.alert_admins')
    def test_conversion_failure_handled(self, \
        mock_alert_admins,
        mock_query_for_metadata
    ):

        mock_job_outputs = {
            'abc': 123
        }
        mock_job_metadata = {
            'end': '2020-10-28T00:05:03.694Z',
            'outputs': mock_job_outputs # doesn't matter what this is, just that the key is there
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

        rcr = RemoteCromwellRunner()
        mock_convert_outputs = mock.MagicMock()
        mock_convert_outputs.side_effect = [OutputConversionException('!!!')]
        rcr._convert_outputs = mock_convert_outputs
        mock_clean_following_success = mock.MagicMock()
        rcr._clean_following_success = mock_clean_following_success
        mock_op = mock.MagicMock()
        rcr.handle_job_success(exec_op, mock_op)

        # query to see that the failure was saved in the db
        self.assertTrue(exec_op.job_failed)
        mock_alert_admins.assert_called()

        mock_convert_outputs.assert_called_once_with(
            exec_op,
            mock_op,
            mock_job_outputs
        )
        mock_clean_following_success.assert_not_called()

    @override_settings(CROMWELL_SERVER_URL='http://mock-cromwell-server:8080')
    @override_settings(OPERATION_LIBRARY_DIR='/data/op_dir')
    @mock.patch('api.runners.remote_cromwell.post_with_retry')
    @mock.patch('api.runners.remote_cromwell.alert_admins')
    def test_submission_failure_raises_ex(self, mock_alert_admins, \
        mock_post_with_retry):
        '''
        Test the situation where we can't reach the Cromwell server. 
        Perhaps it is down/unreachable/etc. In that case, the POST
        request will not succeed.
        '''
        mock_post_with_retry.side_effect = Exception('!!!')

        rcr = RemoteCromwellRunner()
        mock_create_inputs_json = mock.MagicMock()
        mock_copy_workflow_contents = mock.MagicMock()
        mock_create_execution_dir = mock.MagicMock()
        # mock the creation of the execution directory and point
        # it at our folder containing the appropriate WDL files, etc.
        mock_create_execution_dir.return_value = TESTDIR
        rcr._create_inputs_json = mock_create_inputs_json
        rcr._copy_workflow_contents = mock_copy_workflow_contents
        rcr._create_execution_dir = mock_create_execution_dir

        mock_op = mock.MagicMock()
        u = uuid.uuid4()
        mock_op.id = u
        mock_validated_inputs = {'a':1, 'b':2}

        with self.assertRaises(JobSubmissionException):
            rcr.run(self.executed_op, mock_op, mock_validated_inputs)

        mock_create_inputs_json.assert_called_once_with(
            mock_op, 
            f'/data/op_dir/{u}',
            mock_validated_inputs,
            TESTDIR
        )
        mock_copy_workflow_contents.assert_called_once_with(
            f'/data/op_dir/{u}',
            TESTDIR
        )
        mock_alert_admins.assert_called()
        self.assertTrue(self.executed_op.job_failed)
