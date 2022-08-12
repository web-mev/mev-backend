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
from api.views.executed_operation_views import OperationRun
from api.data_structures import StringAttribute
from api.data_structures.submitted_input_or_output import submitted_operation_input_or_output_mapping


TESTDIR = os.path.dirname(__file__)
TESTDIR = os.path.join(TESTDIR, 'operation_test_files')

@mock.patch('api.utilities.ingest_operation.prepare_operation')
@mock.patch('api.utilities.ingest_operation.retrieve_repo_name')
@mock.patch('api.utilities.ingest_operation.check_required_files')
@mock.patch('api.utilities.ingest_operation.retrieve_commit_hash')
@mock.patch('api.utilities.ingest_operation.check_for_repo')
@mock.patch('api.utilities.ingest_operation.clone_repository')
def setup_db_elements(self, op_file, op_dirname, mock_clone_repository, \
    mock_check_for_repo,
    mock_retrieve_commit_hash, \
    mock_check_required_files,
    mock_retrieve_repo_name,
    mock_prepare_operation):

    # make a dummy git repo and copy the valid spec file there:
    dummy_src_path = os.path.join('/tmp', op_dirname)
    os.mkdir(dummy_src_path)
    copy_local_resource(
        os.path.join(TESTDIR, op_file), 
        os.path.join(dummy_src_path, settings.OPERATION_SPEC_FILENAME)
    )

    mock_clone_repository.return_value = dummy_src_path
    mock_retrieve_commit_hash.return_value = 'abcde'
    mock_retrieve_repo_name.return_value = 'my-repo'

    # create a valid operation folder and database object:
    op_uuid = uuid.uuid4()
    op = OperationDbModel.objects.create(id=str(op_uuid))
    perform_operation_ingestion(
        'http://github.com/some-dummy-repo/', 
        str(op_uuid),
        None
    )
    return op

def tear_down_db_elements(self):

    # this is the location where the ingestion will dump the data
    dest_dir = os.path.join(
        settings.OPERATION_LIBRARY_DIR,
        str(self.op.id)
    )
    shutil.rmtree(dest_dir)

    try:
        dest_dir = os.path.join(
            settings.OPERATION_LIBRARY_DIR,
            str(self.non_workspace_op.id)
        )
        shutil.rmtree(dest_dir)
    except Exception as ex:
        pass

class ExecutedOperationListTests(BaseAPITestCase):
    '''
    Tests where we list the ExecutedOperations within a Workspace
    '''
    def setUp(self):
        self.op = setup_db_elements(self, 'valid_workspace_operation.json', 'workspace_op') # creates an Operation to use
        self.non_workspace_op = setup_db_elements(self, 'valid_operation.json', 'non_workspace_op')
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
            operation = self.non_workspace_op,
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


    def test_exec_ops_returns_inactive_ops(self):
        '''
        As operations are updated, we will encounter situations where
        certain Operation instances are marked as 'inactive'. That inactive
        status effectively hides the older tools from being run again. However, a 
        user should still be able to see the results of analyses run using
        that older tool. Whether any frontend tools are able to handle
        updates to any tool outputs is another issue outside the scope
        of the API

        ''' 
        url = reverse('workspace-executed-operation-list',
            kwargs={'workspace_pk': self.workspace.pk}
        )

        inactive_ops = OperationDbModel.objects.filter(active=False)
        if len(inactive_ops) == 0:
            raise ImproperlyConfigured('Need at least one inactive operation to'
                ' run this unit test.'
            )
        inactive_op = inactive_ops[0]

        # create an ExecutedOp for that inactive op
        exec_op_uuid = uuid.uuid4()
        inactive_executed_op = WorkspaceExecutedOperation.objects.create(
            id = exec_op_uuid,
            owner = self.regular_user_1,
            workspace= self.workspace,
            operation = inactive_op,
            job_id = exec_op_uuid, # does not have to be the same as the pk, but is here
            mode = 'foo'
        )

        all_workspace_exec_ops = WorkspaceExecutedOperation.objects.filter(owner=self.regular_user_1)
        all_active_workspace_exec_ops = WorkspaceExecutedOperation.objects.filter(
            owner=self.regular_user_1,
            operation__active = True    
        )
        all_inactive_workspace_exec_ops = WorkspaceExecutedOperation.objects.filter(
            owner=self.regular_user_1,
            operation__active = False    
        )
        response = self.authenticated_regular_client.get(url)
        j = response.json()
        self.assertTrue(len(j)==len(all_workspace_exec_ops))

        queried_active = [x['id'] for x in j if x['operation']['active'] == True]
        queried_inactive = [x['id'] for x in j if x['operation']['active'] == False]
        self.assertCountEqual(
            queried_active,
            [str(x.pk) for x in all_active_workspace_exec_ops]
        )
        self.assertCountEqual(
            queried_inactive,
            [str(x.pk) for x in all_inactive_workspace_exec_ops]
        )

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

        # now test that this user can "see" the new executed op
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
        admin_ops = ExecutedOperation.objects.filter(owner=self.admin_user)
        url = reverse('executed-operation-list')
        response = self.authenticated_admin_client.get(url)
        j = response.json()
        self.assertEqual(len(admin_ops), len(j))
        self.assertTrue(len(all_ops) > len(admin_ops)) # ensure this isn't a trivial test.


class NonWorkspaceExecutedOperationListTests(BaseAPITestCase):
    '''
    Tests where we list the ExecutedOperations not-associated with a Workspace
    '''

    def setUp(self):
        self.op = setup_db_elements(self, 'valid_workspace_operation.json', 'workspace_op') # creates an Operation to use
        self.non_workspace_op = setup_db_elements(self, 'valid_operation.json', 'non_workspace_op')
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

        # create a mock ExecutedOperation which is NOT assoc. with a workspace
        self.exec_op_uuid = uuid.uuid4()
        self.exec_op = ExecutedOperation.objects.create(
            id = self.exec_op_uuid,
            owner = self.regular_user_1,
            operation = self.non_workspace_op,
            job_id = self.exec_op_uuid, # does not have to be the same as the pk, but is here
            mode = 'foo'
        )

    def tearDown(self):
        tear_down_db_elements(self)

    def test_only_one_exec_op_reported(self):
        '''
        In our setup, we only have one ExecutedOperation associated
        with a Workspace. Test that our query to the non-workspace endpoint
        only returns that executed op, NOt the workspace-associated one.
        ''' 
        url = reverse('non-workspace-executed-operation-list')
        all_exec_ops = ExecutedOperation.objects.filter(owner=self.regular_user_1)
        all_workspace_exec_ops = WorkspaceExecutedOperation.objects.filter(owner=self.regular_user_1)
        # check that the test is not trivial (i.e. we should be excluding an 
        # ExecutedOperation that is NOT part of this workspace)
        self.assertTrue((len(all_exec_ops)-len(all_workspace_exec_ops)) > 0)
        all_workspace_op_uuids = [x.id for x in all_workspace_exec_ops]
        non_workspace_ops = [x for x in all_exec_ops if not x.id in all_workspace_op_uuids]
        self.assertTrue(len(non_workspace_ops) > 0)
        self.assertFalse(any([x.operation.workspace_operation for x in non_workspace_ops]))
        response = self.authenticated_regular_client.get(url)
        j = response.json()
        self.assertTrue(len(j)==len(non_workspace_ops))
        self.assertCountEqual([x['id'] for x in j], [str(x.id) for x in non_workspace_ops])

    def test_other_user_request(self):
        '''
        Tests that requests made by another user don't return any records
        (since the test was setup such that the "other user" does not have
        any executed operations)
        '''

        # test for an empty list response
        url = reverse('non-workspace-executed-operation-list')
        reg_user_exec_ops = ExecutedOperation.objects.filter(owner=self.regular_user_1) 
        other_user_exec_ops = ExecutedOperation.objects.filter(owner=self.regular_user_2)
        self.assertTrue(len(other_user_exec_ops) == 0)
        response = self.authenticated_other_client.get(url)
        j = response.json()
        self.assertCountEqual(j, [])

class ExecutedOperationTests(BaseAPITestCase):

    def setUp(self):
        self.op = setup_db_elements(self, 'valid_workspace_operation.json', 'workspace_op') # creates an Operation to use
        self.non_workspace_op = setup_db_elements(self, 'valid_operation.json', 'non_workspace_op')
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
            operation = self.non_workspace_op,
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

    def test_other_user_requests_valid_operation(self):
        '''
        Test the case when there exists an ExecutedOperation
        for user A. User B makes a request for that, so it should be
        rejected as a 404
        '''
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

    def test_admin_user_requests_valid_operation(self):
        '''
        Test the case when there exists an ExecutedOperation
        for user A. An admin can successfully request info
        '''
        response = self.authenticated_admin_client.get(self.good_workspace_exec_op_url)
        # returns 404 since we don't want to 'give away' whether the operation existed.
        self.assertTrue(response.status_code == 404)


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

    def test_job_still_running(self):
        '''
        If a job is still running, simply return 204 (no content)
        '''
        response = self.authenticated_regular_client.get(self.good_workspace_exec_op_url)
        self.assertTrue(response.status_code == 204)
        response = self.authenticated_regular_client.get(self.good_exec_op_url)
        self.assertTrue(response.status_code == 204)

    def test_completed_job_returns_proper_response(self):
        '''
        In this test, the operation has completed so we check that we get info 
        about the completed job
        '''
        # query the op:
        op = WorkspaceExecutedOperation.objects.get(id=self.workspace_exec_op_uuid)

        # mock the finalization is complete by assigning the
        # `execution_stop_datetime` field:
        op.execution_stop_datetime = datetime.datetime.now()
        op.is_finalizing = False
        op.save()

        response = self.authenticated_regular_client.get(self.good_workspace_exec_op_url)
        self.assertTrue(response.status_code == 200)


class OperationListTests(BaseAPITestCase):

    def setUp(self):

        self.op = setup_db_elements(self, 'valid_workspace_operation.json', 'workspace_op')
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

        self.op = setup_db_elements(self, 'valid_workspace_operation.json', 'workspace_op')
        self.url = reverse('operation-detail', kwargs={
            'operation_uuid': str(self.op.id)
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
    @mock.patch('api.views.operation_views.uuid')
    def test_ingest_method_called(self, mock_uuid, mock_ingest):
        '''
        Test that a proper request will call the ingestion function.
        Here, no specific git commit is requested, so the async ingestion
        method is called with 'None'
        '''
        u = uuid.uuid4()
        mock_uuid.uuid4.return_value = u
        mock_git_url = 'https://github.com/foo/'
        payload={'repository_url': mock_git_url}
        response = self.authenticated_admin_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_ingest.delay.assert_called_once_with(str(u), mock_git_url, None)

    @mock.patch('api.views.operation_views.async_ingest_new_operation')
    @mock.patch('api.views.operation_views.uuid')
    def test_ingest_method_called_case2(self, mock_uuid, mock_ingest):
        '''
        Test that a proper request will call the ingestion function. Here,
        we request a specific git commit
        '''
        u = uuid.uuid4()
        mock_uuid.uuid4.return_value = u
        mock_commit_id = 'abcd1234'
        mock_git_url = 'https://github.com/foo/'
        payload={'repository_url': mock_git_url, 'commit_id': mock_commit_id}
        response = self.authenticated_admin_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_ingest.delay.assert_called_once_with(str(u), mock_git_url, mock_commit_id)

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
        The payload has the wrong key. Should be "repository_url"
        '''
        payload={'url':'https://github.com/foo/'}
        response = self.authenticated_admin_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_ingest.delay.assert_not_called()


class OperationRunTests(BaseAPITestCase):

    def setUp(self):
        self.op = setup_db_elements(self, 'valid_workspace_operation.json', 'workspace_op')
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

        # Above we gave gave a bad UUID for workspace, but herea valid one for the operation
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

    @mock.patch('api.views.executed_operation_views.validate_operation_inputs')
    @mock.patch('api.views.executed_operation_views.submit_async_job')
    def test_valid_op_and_workspace_uuid(self, mock_submit_async_job, mock_validate_operation_inputs):
        '''
        Test that a request with a valid workspace UUID
        and valid operation UUID passes
        Note that the validation of the inputs is mocked out
        '''
        # set the mock to return True so that we mock the inputs passing validation
        mock_validate_operation_inputs.return_value = {}

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
        mock_submit_async_job.delay.assert_called()

    @mock.patch('api.views.executed_operation_views.submit_async_job')
    @mock.patch('api.utilities.operations.get_operation_instance_data')
    def test_valid_op_inputs(self, mock_get_operation_instance_data, mock_submit_async_job):
        '''
        The workspace and Operation IDs are fine and this test also checks that the 
        validation of the inputs works.

        In this operation json file, the file input is of VariableDataResource type
        '''
        # set the mock to return True so that we mock the inputs passing validation
        f = os.path.join(
            TESTDIR,
            'valid_workspace_operation.json'
        )
        d = read_operation_json(f)
        mock_get_operation_instance_data.return_value = d

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

    @mock.patch('api.views.executed_operation_views.submit_async_job')
    @mock.patch('api.utilities.operations.get_operation_instance_data')
    def test_valid_op_inputs_case2(self, mock_get_operation_instance_data, mock_submit_async_job):
        '''
        The workspace and Operation IDs are fine and this test also checks that the 
        validation of the inputs works.
        '''
        # set the mock to return True so that we mock the inputs passing validation
        f = os.path.join(
            TESTDIR,
            'valid_workspace_operation_case2.json'
        )
        d = read_operation_json(f)
        mock_get_operation_instance_data.return_value = d

        ops = OperationDbModel.objects.filter(active=True)
        if len(ops) == 0:
            raise ImproperlyConfigured('Need at least one Operation that is active')

        user_workspaces = Workspace.objects.filter(owner=self.regular_user_1)
        if len(user_workspaces) == 0:
            raise ImproperlyConfigured('Need at least one Workspace owned by'
                ' a non-admin user.')

        op = ops[0]

        acceptable_resource_type = d['inputs']['some_file']['spec']['resource_type']
        acceptable_resources = Resource.objects.filter(
            owner=self.regular_user_1,
            is_active=True,
            resource_type=acceptable_resource_type
        )
        acceptable_resources = [x for x in acceptable_resources if len(x.workspaces.all()) > 0]

        if len(acceptable_resources) == 0:
            raise ImproperlyConfigured('Need to have at least one resource with type:'
                ' {t}'.format(
                    t=acceptable_resource_type
                )
            )

        workspace = acceptable_resources[0].workspaces.all()[0]

        valid_inputs = {
            'some_file': str(acceptable_resources[0].id),
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
        

    @mock.patch('api.views.executed_operation_views.submit_async_job')
    @mock.patch('api.views.executed_operation_views.validate_operation_inputs')
    def test_bad_inputs_payload(self, mock_validate_operation_inputs, mock_submit_async_job):
        '''
        The "inputs" key needs to be a dict. When strings were passed, then it 
        caused uncaught errors
        '''
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
            OperationRun.INPUTS: "a string",
            OperationRun.WORKSPACE_UUID: str(workspace.id)
        }
        response = self.authenticated_regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_submit_async_job.delay.assert_not_called()
        mock_validate_operation_inputs.assert_not_called()

    @mock.patch('api.views.executed_operation_views.submit_async_job')
    @mock.patch('api.utilities.operations.get_operation_instance_data')
    def test_observation_and_feature_set_payloads(self, mock_get_operation_instance_data, mock_submit_async_job):
        '''
        Test payloads where the "inputs" key addresses an ObservationSet or FeatureSet
        input.
        '''
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



    @mock.patch('api.views.executed_operation_views.submit_async_job')
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


    @mock.patch('api.views.executed_operation_views.submit_async_job')
    @mock.patch('api.utilities.operations.get_operation_instance_data')
    def test_job_name_set(self, mock_get_operation_instance_data, mock_submit_async_job):
        '''
        Test payloads where the job_name is given
        '''
        f = os.path.join(
            TESTDIR,
            'simple_workspace_op_test.json'
        )
        d = read_operation_json(f)
        mock_get_operation_instance_data.return_value = d

        key = 'some_string'
        submitted_value = 'abc'
        input_dict = {
            key: submitted_value
        }

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
            OperationRun.INPUTS: input_dict,
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
            OperationRun.INPUTS: input_dict,
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

        # now add a job name that has a space- see that this is fine
        mock_submit_async_job.delay.reset_mock()
        job_name = 'foo bar'
        payload = {
            OperationRun.OP_UUID: str(op.id),
            OperationRun.INPUTS: input_dict,
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

        # now an empty string. This is also fine- will just set to be a uuid
        mock_submit_async_job.delay.reset_mock()
        job_name = '    '
        payload = {
            OperationRun.OP_UUID: str(op.id),
            OperationRun.INPUTS: input_dict,
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
            executed_op_uuid,
            payload[OperationRun.INPUTS]
        )

        # now a non-latin character.
        mock_submit_async_job.delay.reset_mock()
        # non-english unicode characters. Not meant to be sensible. Hopefully not vulgar...
        job_name = 'ほ ゑ'
        payload = {
            OperationRun.OP_UUID: str(op.id),
            OperationRun.INPUTS: input_dict,
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

        # now an integer.
        mock_submit_async_job.delay.reset_mock()
        # non-english unicode characters. Not meant to be sensible. Hopefully not vulgar...
        job_name = 2
        job_name_as_str = str(job_name)
        payload = {
            OperationRun.OP_UUID: str(op.id),
            OperationRun.INPUTS: input_dict,
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
            job_name_as_str,
            payload[OperationRun.INPUTS]
        )


class OperationUpdateTests(BaseAPITestCase):

    def setUp(self):
        self.op = setup_db_elements(self, 'valid_workspace_operation.json', 'workspace_op')
        self.establish_clients()

    def test_admin_only(self):
        '''
        Tests that regular users can't use this endpoint
        '''
        url = reverse('operation-update', kwargs={
            'pk': str(self.op.id)
        })
        response = self.authenticated_regular_client.get(url)
        self.assertTrue(response.status_code == 403)

    def test_change_active_status(self):
        '''
        Tests that we can modify the "active" status on an existing operation
        '''
        self.op.active = True
        self.op.save()
        op = OperationDbModel.objects.get(pk=self.op.id)
        self.assertTrue(op.active)
        url = reverse('operation-update', kwargs={
            'pk': str(self.op.id)
        })
        response = self.authenticated_admin_client.patch(url, {'active': False})
        self.assertTrue(response.status_code == 200)
        op = OperationDbModel.objects.get(pk=self.op.id)
        self.assertFalse(op.active)

    def test_bad_update_field_triggers_400(self):
        '''
        Tests that a bad field (even if others are fine) triggers a
        400. This prevents awkward partial updates.
        '''
        self.op.active = True
        self.op.save()
        op = OperationDbModel.objects.get(pk=self.op.id)
        self.assertTrue(op.active)
        url = reverse('operation-update', kwargs={
            'pk': str(self.op.id)
        })
        response = self.authenticated_admin_client.patch(url, 
            {'active': False, 'foo': 'xyz'})
        self.assertTrue(response.status_code == 400)
        op = OperationDbModel.objects.get(pk=self.op.id)

        # Check that the active field as NOT updated
        self.assertTrue(op.active)
