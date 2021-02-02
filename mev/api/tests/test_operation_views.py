import uuid
import unittest.mock as mock
import shutil
import json
import os
import datetime

from django.urls import reverse
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from rest_framework import status

from api.models import Operation as OperationDbModel
from api.models import Workspace, \
    Resource, \
    WorkspaceExecutedOperation, \
    ExecutedOperation
from api.tests.base import BaseAPITestCase
from api.tests import test_settings
from api.utilities.basic_utils import copy_local_resource
from api.utilities.ingest_operation import perform_operation_ingestion
from api.utilities.operations import read_operation_json
from api.views.operation_views import OperationRun


TESTDIR = os.path.dirname(__file__)
TESTDIR = os.path.join(TESTDIR, 'operation_test_files')

@mock.patch('api.utilities.ingest_operation.prepare_operation')
@mock.patch('api.utilities.ingest_operation.retrieve_repo_name')
@mock.patch('api.utilities.ingest_operation.check_required_files')
@mock.patch('api.utilities.ingest_operation.retrieve_commit_hash')
@mock.patch('api.utilities.ingest_operation.clone_repository')
def setup_db_elements(self, mock_clone_repository, \
    mock_retrieve_commit_hash, \
    mock_check_required_files,
    mock_retrieve_repo_name,
    mock_prepare_operation):

    # make a dummy git repo and copy the valid spec file there:
    self.dummy_src_path = os.path.join(settings.BASE_DIR, 'test_dummy_dir')
    os.mkdir(self.dummy_src_path)
    copy_local_resource(
        os.path.join(TESTDIR, 'valid_workspace_operation.json'), 
        os.path.join(self.dummy_src_path, settings.OPERATION_SPEC_FILENAME)
    )

    mock_clone_repository.return_value = self.dummy_src_path
    mock_retrieve_commit_hash.return_value = 'abcde'
    mock_retrieve_repo_name.return_value = 'my-repo'

    # create a valid operation folder and database object:
    self.op_uuid = uuid.uuid4()
    self.op = OperationDbModel.objects.create(id=str(self.op_uuid))
    perform_operation_ingestion(
        'http://github.com/some-dummy-repo/', 
        str(self.op_uuid)
    )

def tear_down_db_elements(self):

    # this is the location where the ingestion will dump the data
    dest_dir = os.path.join(
        settings.OPERATION_LIBRARY_DIR,
        str(self.op_uuid)
    )
    shutil.rmtree(dest_dir)

class ExecutedOperationListTests(BaseAPITestCase):
    '''
    Tests where we list the ExecutedOperations within a Workspace
    '''
    def setUp(self):
        setup_db_elements(self) # creates an Operation to use
        self.establish_clients()

        # need a user's workspace to create an ExecutedOperation
        user_workspaces = Workspace.objects.filter(owner=self.regular_user_1)
        if len(user_workspaces) == 0:
            msg = '''
                Testing not setup correctly.  Please ensure that there is at least one
                Workspace for user {user}.
            '''.format(user=self.regular_user_1)
            raise ImproperlyConfigured(msg)
        self.workspace = user_workspaces[0]

        # create a mock ExecutedOperation
        self.workspace_exec_op_uuid = uuid.uuid4()
        self.workspace_exec_op = WorkspaceExecutedOperation.objects.create(
            id = self.workspace_exec_op_uuid,
            owner = self.regular_user_1,
            workspace= self.workspace,
            operation = self.op,
            job_id = self.workspace_exec_op_uuid, # does not have to be the same as the pk, but is here
            mode = 'foo'
        )
        self.exec_op_uuid = uuid.uuid4()
        self.exec_op = ExecutedOperation.objects.create(
            id = self.exec_op_uuid,
            owner = self.regular_user_1,
            operation = self.op,
            job_id = self.exec_op_uuid, # does not have to be the same as the pk, but is here
            mode = 'foo'
        )

    def tearDown(self):
        tear_down_db_elements(self)

    def test_only_one_exec_op_reported(self):
        '''
        In our setup, we only have one ExecutedOperation associated
        with a Workspace. Test that our query to the workspace-assoc.
        executed ops returns only a single record
        ''' 
        url = reverse('workspace-executed-operation-list',
            kwargs={'workspace_pk': self.workspace.pk}
        )
        all_exec_ops = ExecutedOperation.objects.filter(owner=self.regular_user_1)
        all_workspace_exec_ops = WorkspaceExecutedOperation.objects.filter(owner=self.regular_user_1)
        # check that the test is not trivial (i.e. we should be excluding an 
        # ExecutedOperation that is NOT part of this workspace)
        self.assertTrue((len(all_exec_ops)-len(all_workspace_exec_ops)) > 0)
        response = self.authenticated_regular_client.get(url)
        j = response.json()
        self.assertTrue(len(j)==len(all_workspace_exec_ops))

    def test_list_of_exec_ops(self):
        '''
        In our setup, we only have one ExecutedOperation associated
        with a Workspace. Test that we get one workspace-assoc. executed op
        and one that is NOT associated with a workspace
        ''' 
        url = reverse('executed-operation-list')
        all_exec_ops = ExecutedOperation.objects.filter(owner=self.regular_user_1)
        all_workspace_exec_ops = WorkspaceExecutedOperation.objects.filter(owner=self.regular_user_1)
        self.assertTrue(len(all_exec_ops)==2)
        self.assertTrue(len(all_workspace_exec_ops)==1)
        response = self.authenticated_regular_client.get(url)
        j = response.json()
        self.assertTrue(len(j)==2)
        op_uuids = [x['id'] for x in j]
        self.assertCountEqual(
            op_uuids, 
            [str(self.exec_op_uuid), str(self.workspace_exec_op_uuid)]
        )
        for x in j:
            if x['id'] == str(self.workspace_exec_op_uuid):
                self.assertEqual(x['workspace'], str(self.workspace.pk))
            elif x['id'] == str(self.exec_op_uuid):
                self.assertFalse('workspace' in x.keys())

    def test_other_user_request(self):
        '''
        Tests that requests made by another user don't return any records
        (since the test was setup such that the "other user" does not have
        any executed operations)
        '''

        # test for an empty list response
        url = reverse('executed-operation-list')
        reg_user_exec_ops = ExecutedOperation.objects.filter(owner=self.regular_user_1) 
        other_user_exec_ops = ExecutedOperation.objects.filter(owner=self.regular_user_2)
        self.assertTrue(len(other_user_exec_ops) == 0)
        response = self.authenticated_other_client.get(url)
        j = response.json()
        self.assertCountEqual(j, [])

        # create an ExecutedOp for that other user
        other_user_op_uuid = uuid.uuid4()
        other_user_op = ExecutedOperation.objects.create(
            id = other_user_op_uuid,
            owner = self.regular_user_2,
            operation = self.op,
            job_id = other_user_op_uuid, # does not have to be the same as the pk, but is here
            mode = 'foo'
        )
        other_user_exec_ops = ExecutedOperation.objects.filter(owner=self.regular_user_2)
        self.assertTrue(len(other_user_exec_ops) == 1)
        response = self.authenticated_other_client.get(url)
        j = response.json()
        s1 = set([x.pk for x in reg_user_exec_ops])
        s2 = set([x.pk for x in other_user_exec_ops])
        i_set = list(s1.intersection(s2))
        self.assertTrue(len(i_set) == 0)
        self.assertTrue(len(j)==1)
        self.assertCountEqual(j[0]['id'], str(other_user_op_uuid))

    def test_admin_request(self):
        all_ops = ExecutedOperation.objects.all()
        url = reverse('executed-operation-list')
        response = self.authenticated_admin_client.get(url)
        j = response.json()
        self.assertEqual(len(all_ops), len(j))


class ExecutedOperationTests(BaseAPITestCase):

    def setUp(self):
        setup_db_elements(self) # creates an Operation to use
        self.establish_clients()

        # need a user's workspace to create an ExecutedOperation
        user_workspaces = Workspace.objects.filter(owner=self.regular_user_1)
        if len(user_workspaces) == 0:
            msg = '''
                Testing not setup correctly.  Please ensure that there is at least one
                Workspace for user {user}.
            '''.format(user=self.regular_user_1)
            raise ImproperlyConfigured(msg)
        self.workspace = user_workspaces[0]

        # create a mock ExecutedOperation
        self.workspace_exec_op_uuid = uuid.uuid4()
        self.workspace_exec_op = WorkspaceExecutedOperation.objects.create(
            id = self.workspace_exec_op_uuid,
            owner = self.regular_user_1,
            workspace= self.workspace,
            operation = self.op,
            job_id = self.workspace_exec_op_uuid, # does not have to be the same as the pk, but is here
            mode = 'foo'
        )
        self.exec_op_uuid = uuid.uuid4()
        self.exec_op = ExecutedOperation.objects.create(
            id = self.exec_op_uuid,
            owner = self.regular_user_1,
            operation = self.op,
            job_id = self.exec_op_uuid, # does not have to be the same as the pk, but is here
            mode = 'foo'
        )
        self.good_workspace_exec_op_url = reverse('operation-check',
            kwargs={'exec_op_uuid': self.workspace_exec_op_uuid}
        )
        self.good_exec_op_url = reverse('operation-check',
            kwargs={'exec_op_uuid': self.exec_op_uuid}
        )

    def tearDown(self):
        tear_down_db_elements(self)

    def test_requires_auth(self):
        """
        Test that general requests to the endpoint generate 401
        """
        response = self.regular_client.get(self.good_workspace_exec_op_url)
        self.assertTrue((response.status_code == status.HTTP_401_UNAUTHORIZED) 
        | (response.status_code == status.HTTP_403_FORBIDDEN))

    def test_bad_identifier(self):
        '''
        Tests when the URL gives a UUID which does not correspond to
        an ExecutedOperation
        '''
        # bad uuid
        bad_url = reverse('operation-check',
            kwargs={'exec_op_uuid': uuid.uuid4()}
        )
        response = self.authenticated_regular_client.get(bad_url)
        self.assertTrue(response.status_code == status.HTTP_404_NOT_FOUND)

        # the url above had a valid UUID. now substitute a random string that is NOT
        # a UUID:
        split_url = [x for x in bad_url.split('/') if len(x)>0]
        split_url[2] = 'abc'
        bad_url = '/'.join(split_url)
        response = self.authenticated_regular_client.get(bad_url)
        self.assertTrue(response.status_code == status.HTTP_404_NOT_FOUND)

    @mock.patch('api.views.operation_views.get_runner')
    def test_other_user_requests_valid_operation(self, mock_get_runner):
        '''
        Test the case when there exists an ExecutedOperation
        for user A. User B makes a request for that, so it should be
        rejected as a 404
        '''
        # first try good ID and check that it returns something 'good'
        # indicating that the finalization process has started:
        mock_runner_class = mock.MagicMock()
        mock_runner = mock.MagicMock()
        # mocks that process is still running so it shoudl return 204 status
        mock_runner.check_status.return_value = False
        mock_runner_class.return_value = mock_runner
        mock_get_runner.return_value = mock_runner_class
        response = self.authenticated_regular_client.get(self.good_workspace_exec_op_url)
        self.assertTrue(response.status_code == 204)
        response = self.authenticated_regular_client.get(self.good_exec_op_url)
        self.assertTrue(response.status_code == 204)

        # now try making the request as another user and it should fail
        # with a 404 not found
        response = self.authenticated_other_client.get(self.good_workspace_exec_op_url)
        self.assertTrue(response.status_code == 404)
        response = self.authenticated_other_client.get(self.good_exec_op_url)
        self.assertTrue(response.status_code == 404)

    @mock.patch('api.views.operation_views.get_runner')
    def test_admin_user_requests_valid_operation(self, mock_get_runner):
        '''
        Test the case when there exists an ExecutedOperation
        for user A. An admin can successfully request info
        '''
        mock_runner_class = mock.MagicMock()
        mock_runner = mock.MagicMock()
        # mocks that process is still running so it shoudl return 204 status
        mock_runner.check_status.return_value = False 
        mock_runner_class.return_value = mock_runner
        mock_get_runner.return_value = mock_runner_class
        response = self.authenticated_admin_client.get(self.good_workspace_exec_op_url)
        self.assertTrue(response.status_code == 204)

    @mock.patch('api.views.operation_views.get_runner')
    @mock.patch('api.views.operation_views.finalize_executed_op')
    def test_completed_job_starts_finalizing(self, 
        mock_finalize_executed_op, mock_get_runner):
        '''
        Tests the case where a job has completed, but
        nothing has happened as far as "finalization".
        Requests to this endpoint should start that process
        '''
        mock_runner_class = mock.MagicMock()
        mock_runner = mock.MagicMock()
        # mocks that process is still running so it shoudl return 204 status
        mock_runner.check_status.return_value = True 
        mock_runner_class.return_value = mock_runner
        mock_get_runner.return_value = mock_runner_class
        response = self.authenticated_regular_client.get(self.good_workspace_exec_op_url)
        mock_finalize_executed_op.delay.assert_called_with(str(self.workspace_exec_op_uuid))
        self.assertTrue(response.status_code == 202)

    def test_request_to_finalizing_process_returns_208(self):
        '''
        If an ExecutedOperation is still in the process of finalizing,
        return 208 ("already reported") to inform that things are still processing.
        '''
        exec_op_uuid = uuid.uuid4()
        exec_op = WorkspaceExecutedOperation.objects.create(
            id = exec_op_uuid,
            owner = self.regular_user_1,
            workspace= self.workspace,
            operation = self.op,
            job_id = exec_op_uuid, # does not have to be the same as the pk, but is here
            mode = 'foo',
            is_finalizing = True
        )
        url = reverse('operation-check',
            kwargs={'exec_op_uuid': exec_op_uuid}
        )
        response = self.authenticated_regular_client.get(url)
        self.assertTrue(response.status_code == 208)

        # test the non-workspace associated ExecutedOperation
        exec_op_uuid = uuid.uuid4()
        exec_op = ExecutedOperation.objects.create(
            id = exec_op_uuid,
            owner = self.regular_user_1,
            operation = self.op,
            job_id = exec_op_uuid, # does not have to be the same as the pk, but is here
            mode = 'foo',
            is_finalizing = True
        )
        url = reverse('operation-check',
            kwargs={'exec_op_uuid': exec_op_uuid}
        )
        response = self.authenticated_regular_client.get(url)
        self.assertTrue(response.status_code == 208)

    @mock.patch('api.views.operation_views.get_runner')
    def test_job_still_running(self, mock_get_runner):
        '''
        If a job is still running, simply return 204 (no content)
        '''
        # first try good ID and check that it returns something 'good'
        # indicating that the finalization process has started:
        mock_runner_class = mock.MagicMock()
        mock_runner = mock.MagicMock()
        # mocks that process is still running so it shoudl return 204 status
        mock_runner.check_status.return_value = False
        mock_runner_class.return_value = mock_runner
        mock_get_runner.return_value = mock_runner_class
        response = self.authenticated_regular_client.get(self.good_workspace_exec_op_url)
        self.assertTrue(response.status_code == 204)
        response = self.authenticated_regular_client.get(self.good_exec_op_url)
        self.assertTrue(response.status_code == 204)

    @mock.patch('api.views.operation_views.get_runner')
    @mock.patch('api.views.operation_views.finalize_executed_op')
    def test_multiple_requests_case1(self, 
        mock_finalize_executed_op, mock_get_runner):
        '''
        In this test, the first request kicks off the process to finalize the 
        ExecutedOperation. A secondary request arrives before that process
        is complete, and the API should respond with the 208 code to let it 
        know that things are still processing.
        '''
        # query the op to start to ensure the test is setup properly
        op = WorkspaceExecutedOperation.objects.get(id=self.workspace_exec_op_uuid)
        self.assertFalse(op.is_finalizing)

        mock_runner_class = mock.MagicMock()
        mock_runner = mock.MagicMock()
        # mocks that process has completed
        mock_runner.check_status.return_value = True 
        mock_runner_class.return_value = mock_runner
        mock_get_runner.return_value = mock_runner_class
        response = self.authenticated_regular_client.get(self.good_workspace_exec_op_url)
        #mock_finalize_executed_op.delay.assert_called_with(str(self.workspace_exec_op_uuid))
        self.assertTrue(response.status_code == 202)

        # query the op:
        op = WorkspaceExecutedOperation.objects.get(id=self.workspace_exec_op_uuid)
        self.assertTrue(op.is_finalizing)

        # make a second query. since the process is finalizing, should return 208
        response = self.authenticated_regular_client.get(self.good_workspace_exec_op_url)
        self.assertTrue(response.status_code == 208)

        # check that the finalization was only called once.
        mock_finalize_executed_op.delay.assert_called_once_with(str(self.workspace_exec_op_uuid))

        # now check for the non-workspace ExecOp
        mock_finalize_executed_op.reset_mock()
        op = ExecutedOperation.objects.get(id=self.exec_op_uuid)
        self.assertFalse(op.is_finalizing)

        response = self.authenticated_regular_client.get(self.good_exec_op_url)
        self.assertTrue(response.status_code == 202)

        # query the op:
        op = ExecutedOperation.objects.get(id=self.exec_op_uuid)
        self.assertTrue(op.is_finalizing)

        # make a second query. since the process is finalizing, should return 208
        response = self.authenticated_regular_client.get(self.good_exec_op_url)
        self.assertTrue(response.status_code == 208)

        # check that the finalization was only called once.
        mock_finalize_executed_op.delay.assert_called_once_with(str(self.exec_op_uuid))



    @mock.patch('api.views.operation_views.get_runner')
    @mock.patch('api.views.operation_views.finalize_executed_op')
    def test_multiple_requests_case2(self,
        mock_finalize_executed_op, mock_get_runner):
        '''
        In this test, the first request kicks off the process to finalize the 
        ExecutedOperation. A secondary request after that process
        is complete, and the API should respond with the outputs
        '''
        # query the op to start to ensure the test is setup properly
        op = WorkspaceExecutedOperation.objects.get(id=self.workspace_exec_op_uuid)
        self.assertFalse(op.is_finalizing)

        mock_runner_class = mock.MagicMock()
        mock_runner = mock.MagicMock()
        # mocks that process is complete
        mock_runner.check_status.return_value = True 
        mock_runner_class.return_value = mock_runner
        mock_get_runner.return_value = mock_runner_class
        response = self.authenticated_regular_client.get(self.good_workspace_exec_op_url)
        mock_finalize_executed_op.delay.assert_called_with(str(self.workspace_exec_op_uuid))
        self.assertTrue(response.status_code == 202)

        # query the op:
        op = WorkspaceExecutedOperation.objects.get(id=self.workspace_exec_op_uuid)
        self.assertTrue(op.is_finalizing)

        # mock the finalization is complete by assigning the
        # `execution_stop_datetime` field:
        op.execution_stop_datetime = datetime.datetime.now()
        op.is_finalizing = False
        op.save()

        # make a second query. since the process is finalizing, should return 208
        response = self.authenticated_regular_client.get(self.good_workspace_exec_op_url)
        self.assertTrue(response.status_code == 200)

        # check the non-workspace ExecOp:
        mock_finalize_executed_op.reset_mock()
        op = ExecutedOperation.objects.get(id=self.exec_op_uuid)
        self.assertFalse(op.is_finalizing)

        response = self.authenticated_regular_client.get(self.good_exec_op_url)
        mock_finalize_executed_op.delay.assert_called_with(str(self.exec_op_uuid))
        self.assertTrue(response.status_code == 202)

        # query the op:
        op = ExecutedOperation.objects.get(id=self.exec_op_uuid)
        self.assertTrue(op.is_finalizing)

        # mock the finalization is complete by assigning the
        # `execution_stop_datetime` field:
        op.execution_stop_datetime = datetime.datetime.now()
        op.is_finalizing = False
        op.save()

        # make a second query. since the process is finalizing, should return 208
        response = self.authenticated_regular_client.get(self.good_exec_op_url)
        self.assertTrue(response.status_code == 200)


class OperationListTests(BaseAPITestCase):

    def setUp(self):

        setup_db_elements(self)
        self.url = reverse('operation-list')
        self.establish_clients()

    def tearDown(self):
        tear_down_db_elements(self)

    def test_list_operations_requires_auth(self):
        """
        Test that general requests to the endpoint generate 401
        """
        response = self.regular_client.get(self.url)
        self.assertTrue((response.status_code == status.HTTP_401_UNAUTHORIZED) 
        | (response.status_code == status.HTTP_403_FORBIDDEN))
    
    def test_inactive_operations_filtered(self):
        '''
        If (somehow) a directory containing an operation was removed,
        assure that we handle it well. In this 
        '''
        num_total_ops = len(OperationDbModel.objects.all())

        n0 = len(OperationDbModel.objects.filter(active=True))
        # create an Operation instance that is not active (default behavior)
        u = uuid.uuid4()
        o = OperationDbModel.objects.create(id=u, name='foo')

        response = self.authenticated_regular_client.get(self.url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)

        n1 = len(OperationDbModel.objects.filter(active=True))
        self.assertEqual(n1-n0,0) # number of active instances unchanged
        n2 = len(OperationDbModel.objects.all())
        self.assertEqual(n2-num_total_ops,1)

    def test_inconsistent_db_and_dir(self):
        '''
        If (somehow) a directory containing an operation was removed,
        assure that we handle it well. In this 
        '''
        # create an Operation instance that does NOT have a corresponding folder
        u = uuid.uuid4()
        o = OperationDbModel.objects.create(id=u, name='foo', active=True)

        response = self.authenticated_regular_client.get(self.url, format='json')
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class OperationDetailTests(BaseAPITestCase):

    def setUp(self):

        setup_db_elements(self)
        self.url = reverse('operation-detail', kwargs={
            'operation_uuid': str(self.op_uuid)
        })
        self.establish_clients()

    def tearDown(self):
        tear_down_db_elements(self)

    def test_operation_detail_requires_auth(self):
        """
        Test that general requests to the endpoint generate 401
        """
        response = self.regular_client.get(self.url)
        self.assertTrue((response.status_code == status.HTTP_401_UNAUTHORIZED) 
        | (response.status_code == status.HTTP_403_FORBIDDEN))

    def test_successful_query(self):
        '''
        Test that the response works for a good request
        '''

        # query the existing instance, see that response is OK:
        response = self.authenticated_regular_client.get(self.url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_inconsistent_db_and_dir(self):
        '''
        If (somehow) a directory containing an operation was removed,
        assure that we handle it well.
        '''
        # create an Operation instance that does NOT have a corresponding folder
        # Note that it starts as inactive
        u = uuid.uuid4()
        o = OperationDbModel.objects.create(id=u, name='foo')

        # query this 'new' instance which has a database inconsistency:
        url = reverse('operation-detail', kwargs={
            'operation_uuid': str(u)
        })
        response = self.authenticated_regular_client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # change the instance to be active. Now if the folder is missing, then it's
        # a real error (500)
        o.active=True
        o.save()

        response = self.authenticated_regular_client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    def test_unknown_operation_returns_404(self):

        unknown_uuid = uuid.uuid4()
        url = reverse('operation-detail', kwargs={
            'operation_uuid': str(unknown_uuid)
        })
        response = self.authenticated_regular_client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class OperationAddTests(BaseAPITestCase):

    def setUp(self):
        self.url = reverse('operation-create')
        self.establish_clients()

    @mock.patch('api.views.operation_views.async_ingest_new_operation')
    def test_admin_only(self, mock_ingest):
        '''
        Test that only admins can access the Operation create endpoint.
        '''
        payload={'repository_url':'https://github.com/foo/'}
        response = self.authenticated_regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        mock_ingest.delay.assert_not_called()


    @mock.patch('api.views.operation_views.async_ingest_new_operation')
    def test_ingest_method_called(self, mock_ingest):
        '''
        Test that a proper request will call the ingestion function.
        '''
        payload={'repository_url':'https://github.com/foo/'}
        response = self.authenticated_admin_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_ingest.delay.assert_called()

    @mock.patch('api.views.operation_views.async_ingest_new_operation')
    def test_invalid_domain(self, mock_ingest):
        '''
        Payload is valid, but the repository domain was not among the 
        acceptable domains
        '''
        payload={'repository_url':'https://bitbucket.com/foo/'}
        response = self.authenticated_admin_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_ingest.delay.assert_not_called()

    @mock.patch('api.views.operation_views.async_ingest_new_operation')
    def test_bad_payload(self, mock_ingest):
        '''
        The payload has the wrong key.
        '''
        payload={'url':'https://github.com/foo/'}
        response = self.authenticated_admin_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_ingest.delay.assert_not_called()


class OperationRunTests(BaseAPITestCase):

    def setUp(self):
        setup_db_elements(self)
        self.url = reverse('operation-run')
        self.establish_clients()

    def test_missing_keys_returns_400_error(self):
        '''
        We require certain keys in the payload. If any are
        missing, check that we return 400
        '''
        payload = {OperationRun.OP_UUID: 'abc'}
        response = self.authenticated_regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        s = response.json()
        expected_response = {
            OperationRun.INPUTS: OperationRun.REQUIRED_MESSAGE
        }
        self.assertDictEqual(s, expected_response)

    def test_bad_uuid_returns_400_error(self):
        '''
        The UUID for the operation or workspace is not a real UUID.
        '''
        payload = {
            OperationRun.OP_UUID: 'abc',
            OperationRun.INPUTS: [],
            OperationRun.WORKSPACE_UUID: 'abc'
        }
        response = self.authenticated_regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        s = response.json()
        expected_response = {
            OperationRun.OP_UUID: OperationRun.BAD_UUID_MESSAGE.format(
                field=OperationRun.OP_UUID,
                uuid='abc'   
            )
        }
        self.assertDictEqual(s, expected_response)

        # now give a bad UUID for workspace, but a valid one for the operation
        ops = OperationDbModel.objects.filter(active=True)
        if len(ops) == 0:
            raise ImproperlyConfigured('Need at least one Operation that is active')

        op = ops[0]
        # make it a workspace operation if it's not already
        op.workspace_operation = True
        op.save()
        payload = {
            OperationRun.OP_UUID: str(op.id),
            OperationRun.INPUTS: [],
            OperationRun.WORKSPACE_UUID: 'abc'
        }
        response = self.authenticated_regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        s = response.json()
        expected_response = {
            OperationRun.WORKSPACE_UUID: OperationRun.BAD_UUID_MESSAGE.format(
                field=OperationRun.WORKSPACE_UUID,
                uuid='abc'   
            )
        }
        self.assertDictEqual(s, expected_response)

    def test_not_found_workspace_uuid(self):
        '''
        Test the case where a valid UUID is given for the workspace field, 
        but there is no database object for that
        '''

        # now give a bad UUID for workspace, but a valid one for the operation
        ops = OperationDbModel.objects.filter(active=True)
        if len(ops) == 0:
            raise ImproperlyConfigured('Need at least one Operation that is active')

        workspace_uuid = uuid.uuid4()

        op = ops[0]
        # make it a workspace operation if it's not already
        op.workspace_operation = True
        op.save()
        payload = {
            OperationRun.OP_UUID: str(op.id),
            OperationRun.INPUTS: [],
            OperationRun.WORKSPACE_UUID: str(workspace_uuid)
        }
        response = self.authenticated_regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        s = response.json()
        expected_response = {
            OperationRun.WORKSPACE_UUID: OperationRun.NOT_FOUND_MESSAGE.format(
                uuid=str(workspace_uuid)  
            )
        }
        self.assertDictEqual(s, expected_response)

    def test_valid_op_and_other_workspace_uuid(self):
        '''
        Test that a request with a valid workspace UUID
        owned by another user fails.
        '''

        # now give a bad UUID for workspace, but a valid one for the operation
        ops = OperationDbModel.objects.filter(active=True)
        if len(ops) == 0:
            raise ImproperlyConfigured('Need at least one Operation that is active')

        # get a workspace for a different user. The Workspace is valid, but is
        # not owned by the client making the request.
        user_workspaces = Workspace.objects.filter(owner=self.regular_user_2)
        if len(user_workspaces) == 0:
            raise ImproperlyConfigured('Need at least one Workspace owned by'
                ' the OTHER non-admin user.')

        workspace = user_workspaces[0]
        op = ops[0]
        # make it a workspace operation if it's not already
        op.workspace_operation = True
        op.save()
        payload = {
            OperationRun.OP_UUID: str(op.id),
            OperationRun.INPUTS: [],
            OperationRun.WORKSPACE_UUID: str(workspace.id)
        }
        response = self.authenticated_regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        s = response.json()
        expected_response = {
            OperationRun.WORKSPACE_UUID: OperationRun.NOT_FOUND_MESSAGE.format(
                uuid=str(workspace.id)  
            )
        }
        self.assertDictEqual(s, expected_response)

    @mock.patch('api.views.operation_views.validate_operation_inputs')
    def test_valid_op_and_workspace_uuid(self, mock_validate_operation_inputs):
        '''
        Test that a request with a valid workspace UUID
        and valid operation UUID passes
        Note that the validation of the inputs is mocked out
        '''
        # set the mock to return True so that we mock the inputs passing validation
        mock_validate_operation_inputs.return_value = {}

        # now give a bad UUID for workspace, but a valid one for the operation
        ops = OperationDbModel.objects.filter(active=True)
        if len(ops) == 0:
            raise ImproperlyConfigured('Need at least one Operation that is active')

        user_workspaces = Workspace.objects.filter(owner=self.regular_user_1)
        if len(user_workspaces) == 0:
            raise ImproperlyConfigured('Need at least one Workspace owned by'
                ' a non-admin user.')

        workspace = user_workspaces[0]
        op = ops[0]
        payload = {
            OperationRun.OP_UUID: str(op.id),
            OperationRun.INPUTS: {'foo': 1, 'bar':'abc'},
            OperationRun.WORKSPACE_UUID: str(workspace.id)
        }
        response = self.authenticated_regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @mock.patch('api.views.operation_views.submit_async_job')
    @mock.patch('api.utilities.operations.get_operation_instance_data')
    def test_valid_op_inputs(self, mock_get_operation_instance_data, mock_submit_async_job):
        '''
        The workspace and Operation IDs are fine and this test also checks that the 
        validation of the inputs works.
        '''
        # set the mock to return True so that we mock the inputs passing validation
        f = os.path.join(
            TESTDIR,
            'valid_workspace_operation.json'
        )
        d = read_operation_json(f)
        mock_get_operation_instance_data.return_value = d

        # now give a bad UUID for workspace, but a valid one for the operation
        ops = OperationDbModel.objects.filter(active=True)
        if len(ops) == 0:
            raise ImproperlyConfigured('Need at least one Operation that is active')

        user_workspaces = Workspace.objects.filter(owner=self.regular_user_1)
        if len(user_workspaces) == 0:
            raise ImproperlyConfigured('Need at least one Workspace owned by'
                ' a non-admin user.')

        op = ops[0]

        acceptable_resource_types = d['inputs']['count_matrix']['spec']['resource_types']
        acceptable_resources = []
        for t in acceptable_resource_types:
            r = Resource.objects.filter(
                owner=self.regular_user_1,
                is_active=True,
                resource_type=t
            )
            r = [x for x in r if len(x.workspaces.all()) > 0]
            if len(r) > 0:
                acceptable_resources.extend(r)

        if len(acceptable_resources) == 0:
            raise ImproperlyConfigured('Need to have at least one resource with types'
                ' in: {typelist}'.format(
                    typelist=', '.join(acceptable_resource_types)
                )
            )

        workspace = acceptable_resources[0].workspaces.all()[0]

        valid_inputs = {
            'count_matrix': str(acceptable_resources[0].id),
            'p_val': 0.1
        }

        payload = {
            OperationRun.OP_UUID: str(op.id),
            OperationRun.INPUTS: valid_inputs,
            OperationRun.WORKSPACE_UUID: str(workspace.id)
        }
        response = self.authenticated_regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_submit_async_job.delay.assert_called()
        mock_submit_async_job.delay.reset_mock()

        invalid_inputs = {
            'count_matrix': str(acceptable_resources[0].id),
            'p_val': 1.1 # too high for limits
        }

        payload = {
            OperationRun.OP_UUID: str(op.id),
            OperationRun.INPUTS: invalid_inputs,
            OperationRun.WORKSPACE_UUID: str(workspace.id)
        }
        response = self.authenticated_regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_submit_async_job.delay.assert_not_called()
        mock_submit_async_job.delay.reset_mock()

        invalid_inputs = {
            'count_matrix': str(uuid.uuid4()),
        }

        payload = {
            OperationRun.OP_UUID: str(op.id),
            OperationRun.INPUTS: invalid_inputs,
            OperationRun.WORKSPACE_UUID: str(workspace.id)
        }
        response = self.authenticated_regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_submit_async_job.delay.assert_not_called()

    @mock.patch('api.views.operation_views.submit_async_job')
    @mock.patch('api.utilities.operations.get_operation_instance_data')
    def test_bad_inputs_payload(self, mock_get_operation_instance_data, mock_submit_async_job):
        '''
        The "inputs" key needs to be a dict. When strings were passed, then it 
        caused uncaught errors
        '''
        # set the mock to return True so that we mock the inputs passing validation
        f = os.path.join(
            TESTDIR,
            'valid_workspace_operation.json'
        )
        d = read_operation_json(f)
        mock_get_operation_instance_data.return_value = d

        # now give a bad UUID for workspace, but a valid one for the operation
        ops = OperationDbModel.objects.filter(active=True)
        if len(ops) == 0:
            raise ImproperlyConfigured('Need at least one Operation that is active')

        user_workspaces = Workspace.objects.filter(owner=self.regular_user_1)
        if len(user_workspaces) == 0:
            raise ImproperlyConfigured('Need at least one Workspace owned by'
                ' a non-admin user.')

        workspace = user_workspaces[0]
        op = ops[0]

        acceptable_resource_types = d['inputs']['count_matrix']['spec']['resource_types']
        acceptable_resources = []
        for t in acceptable_resource_types:
            r = Resource.objects.filter(
                owner=self.regular_user_1,
                is_active=True,
                resource_type=t
            )
            if len(r) > 0:
                acceptable_resources.extend(r)

        if len(acceptable_resources) == 0:
            raise ImproperlyConfigured('Need to have at least one resource with types'
                ' in: {typelist}'.format(
                    typelist=', '.join(acceptable_resource_types)
                )
            )

        payload = {
            OperationRun.OP_UUID: str(op.id),
            OperationRun.INPUTS: "a string",
            OperationRun.WORKSPACE_UUID: str(workspace.id)
        }
        response = self.authenticated_regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_submit_async_job.delay.assert_not_called()

    @mock.patch('api.views.operation_views.submit_async_job')
    @mock.patch('api.utilities.operations.get_operation_instance_data')
    def test_observation_and_feature_set_payloads(self, mock_get_operation_instance_data, mock_submit_async_job):
        '''
        Test payloads where the "inputs" key addresses an ObservationSet or FeatureSet
        input.
        '''
        # set the mock to return True so that we mock the inputs passing validation
        f = os.path.join(
            TESTDIR,
            'obs_set_test.json'
        )
        d = read_operation_json(f)
        mock_get_operation_instance_data.return_value = d

        valid_obs_1 = {
            'id': 'foo',
            'attributes': {
                'treatment': {'attribute_type':'String','value':'A'}
            }
        }
        valid_obs_2 = {
            'id': 'bar',
            'attributes': {
                'treatment': {'attribute_type':'String','value':'B'}
            }
        }

        valid_obs_set = {
            'multiple': True,
            'elements': [
                valid_obs_1,
                valid_obs_2
            ]
        }

        # now give a bad UUID for workspace, but a valid one for the operation
        ops = OperationDbModel.objects.filter(active=True)
        if len(ops) == 0:
            raise ImproperlyConfigured('Need at least one Operation that is active')

        user_workspaces = Workspace.objects.filter(owner=self.regular_user_1)
        if len(user_workspaces) == 0:
            raise ImproperlyConfigured('Need at least one Workspace owned by'
                ' a non-admin user.')

        workspace = user_workspaces[0]
        op = ops[0]

        payload = {
            OperationRun.OP_UUID: str(op.id),
            OperationRun.INPUTS: {
                'obs_set_type': valid_obs_set,
                'obs_type': valid_obs_1
            },
            OperationRun.WORKSPACE_UUID: str(workspace.id)
        }
        response = self.authenticated_regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_submit_async_job.delay.assert_called()
        mock_submit_async_job.delay.reset_mock()

        # test where the payload is bad:
        invalid_obs_set = {
            'multiple': False, # inconsistent with the >1 elements below
            'elements': [
                valid_obs_1,
                valid_obs_2
            ]
        }
        payload = {
            OperationRun.OP_UUID: str(op.id),
            OperationRun.INPUTS: {
                'obs_set_type': invalid_obs_set,
                'obs_type': valid_obs_1
            },
            OperationRun.WORKSPACE_UUID: str(workspace.id)
        }
        response = self.authenticated_regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_submit_async_job.delay.assert_not_called()
        mock_submit_async_job.delay.reset_mock()


        # test where the payload is bad:
        invalid_obs_set = {
            'multiple': False, # inconsistent with the >1 elements below
            'elements': [
                {    # missing 'id' key
                    'attributes': {}
                }
            ]
        }
        payload = {
            OperationRun.OP_UUID: str(op.id),
            OperationRun.INPUTS: {
                'obs_set_type': invalid_obs_set,
                'obs_type': valid_obs_1
            },
            OperationRun.WORKSPACE_UUID: str(workspace.id)
        }
        response = self.authenticated_regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_submit_async_job.delay.assert_not_called()
        mock_submit_async_job.delay.reset_mock()



    @mock.patch('api.views.operation_views.submit_async_job')
    @mock.patch('api.utilities.operations.get_operation_instance_data')
    def test_proper_call_with_nonworkspace_op(self, mock_get_operation_instance_data, mock_submit_async_job):
        '''
        Test that the proper call is made when the Operation is not a workspace-assoc.
        Operation.
        '''
        # set the mock to return True so that we mock the inputs passing validation
        f = os.path.join(
            TESTDIR,
            'simple_op_test.json'
        )
        d = read_operation_json(f)
        mock_get_operation_instance_data.return_value = d

        # now give a bad UUID for workspace, but a valid one for the operation
        ops = OperationDbModel.objects.filter(active=True)
        if len(ops) == 0:
            raise ImproperlyConfigured('Need at least one Operation that is active')

        op = ops[0]
        # make it a non-workspace operation if it's not already
        op.workspace_operation = False
        op.save()

        # first try a payload where the job_name field is not given.
        # Check that the given name is the same as the execution job_id
        payload = {
            OperationRun.OP_UUID: str(op.id),
            OperationRun.INPUTS: {
                'some_string': 'abc'
            }
        }
        response = self.authenticated_regular_client.post(self.url, data=payload, format='json')
        response_json = response.json()
        executed_op_uuid = response_json['executed_operation_id']
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_submit_async_job.delay.assert_called_once_with(
            uuid.UUID(executed_op_uuid), 
            op.id, 
            self.regular_user_1.pk,
            None, 
            executed_op_uuid,
            payload[OperationRun.INPUTS]
        )


    @mock.patch('api.views.operation_views.submit_async_job')
    @mock.patch('api.utilities.operations.get_operation_instance_data')
    def test_job_name_set(self, mock_get_operation_instance_data, mock_submit_async_job):
        '''
        Test payloads where the job_name is given
        '''
        # set the mock to return True so that we mock the inputs passing validation
        f = os.path.join(
            TESTDIR,
            'simple_workspace_op_test.json'
        )
        d = read_operation_json(f)
        mock_get_operation_instance_data.return_value = d

        # now give a bad UUID for workspace, but a valid one for the operation
        ops = OperationDbModel.objects.filter(active=True)
        if len(ops) == 0:
            raise ImproperlyConfigured('Need at least one Operation that is active')

        user_workspaces = Workspace.objects.filter(owner=self.regular_user_1)
        if len(user_workspaces) == 0:
            raise ImproperlyConfigured('Need at least one Workspace owned by'
                ' a non-admin user.')

        workspace = user_workspaces[0]
        op = ops[0]
        # make it a workspace operation if it's not already
        op.workspace_operation = True
        op.save()

        # first try a payload where the job_name field is not given.
        # Check that the given name is the same as the execution job_id
        payload = {
            OperationRun.OP_UUID: str(op.id),
            OperationRun.INPUTS: {
                'some_string': 'abc'
            },
            OperationRun.WORKSPACE_UUID: str(workspace.id)
        }
        response = self.authenticated_regular_client.post(self.url, data=payload, format='json')
        response_json = response.json()
        executed_op_uuid = response_json['executed_operation_id']
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_submit_async_job.delay.assert_called_once_with(
            uuid.UUID(executed_op_uuid), 
            op.id, 
            self.regular_user_1.pk,
            workspace.id, 
            executed_op_uuid,
            payload[OperationRun.INPUTS]
        )
        mock_submit_async_job.delay.reset_mock()

        # now add a job name- see that it gets sent to the async method
        job_name = 'foo'
        payload = {
            OperationRun.OP_UUID: str(op.id),
            OperationRun.INPUTS: {
                'some_string': 'abc'
            },
            OperationRun.WORKSPACE_UUID: str(workspace.id),
            OperationRun.JOB_NAME: job_name
        }
        response = self.authenticated_regular_client.post(self.url, data=payload, format='json')
        response_json = response.json()
        executed_op_uuid = response_json['executed_operation_id']
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_submit_async_job.delay.assert_called_once_with(
            uuid.UUID(executed_op_uuid), 
            op.id, 
            self.regular_user_1.pk,
            workspace.id, 
            job_name,
            payload[OperationRun.INPUTS]
        )