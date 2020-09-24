import uuid
import unittest.mock as mock
import shutil
import json
import os

from django.urls import reverse
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from rest_framework import status

from api.models import Operation as OperationDbModel
from api.models import Workspace, Resource
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
        os.path.join(TESTDIR, 'valid_operation.json'), 
        os.path.join(self.dummy_src_path, settings.OPERATION_SPEC_FILENAME)
    )

    mock_clone_repository.return_value = self.dummy_src_path
    mock_retrieve_commit_hash.return_value = 'abcde'
    mock_retrieve_repo_name.return_value = 'my-repo'

    # create a valid operation folder and database object:
    self.op_uuid = uuid.uuid4()
    o = OperationDbModel.objects.create(id=str(self.op_uuid))
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
        self.assertEqual(n2,2)

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
            OperationRun.WORKSPACE_UUID: OperationRun.REQUIRED_MESSAGE,
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
            'valid_operation.json'
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
            'valid_operation.json'
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
                'treatment': 'A'
            }
        }
        valid_obs_2 = {
            'id': 'bar',
            'attributes': {
                'treatment': 'B'
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