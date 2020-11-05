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
from api.models.workspace import Workspace

# the api/tests dir
TESTDIR = os.path.dirname(__file__)
TESTDIR = os.path.join(TESTDIR, 'operation_test_files', 'demo_cromwell_workflow')

class RemoteCromwellRunnerTester(BaseAPITestCase):

    def setUp(self):
        os.environ['CROMWELL_SERVER_URL'] = 'http://mock-cromwell-server:8080'
        os.environ['CROMWELL_BUCKET'] = 'my-bucket'

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

        ops = Operation.objects.all()
        if len(ops) == 0:
            raise ImproperlyConfigured('Need at least one Operation to run this test.')
        op = ops[0]
        workspaces = Workspace.objects.all()
        if len(workspaces) == 0:
            raise ImproperlyConfigured('Need at least one Workspace to run this test.')
        workspace = workspaces[0]
        exec_op_pk = uuid.uuid4()
        job_name = 'foo'
        exec_op = ExecutedOperation.objects.create(
            id=exec_op_pk,
            workspace=workspace,
            job_name = job_name,
            inputs = {},
            operation = op,
            mode = 'cromwell',
            status = ExecutedOperation.SUBMITTED
        )
        rcr = RemoteCromwellRunner()
        rcr.handle_submission_response(mock_response, exec_op)
        self.assertEqual(exec_op.job_id, str(u))
        self.assertEqual(exec_op.execution_start_datetime, now)
        print(exec_op.status)

        mock_response.status_code = 400
        rcr.handle_submission_response(mock_response, exec_op)
        mock_alert_admins.assert_called()

    def test_handle_job_check(self):
        '''
        To check on a job, the user will submit a request-- check
        that the various options are handled well.
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
        To check on a job, the user will submit a request-- check
        that the various options are handled well. This version mocks the
        get call.
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