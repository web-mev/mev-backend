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
from api.tests.base import BaseAPITestCase
from api.tests import test_settings
from api.utilities.basic_utils import copy_local_resource
from api.utilities.ingest_operation import perform_operation_ingestion

TESTDIR = os.path.dirname(__file__)
TESTDIR = os.path.join(TESTDIR, 'operation_test_files')

@mock.patch('api.utilities.ingest_operation.retrieve_commit_hash')
@mock.patch('api.utilities.ingest_operation.clone_repository')
def setup_db_elements(self, mock_clone_repository, mock_retrieve_commit_hash):

    # make a dummy git repo and copy the valid spec file there:
    self.dummy_src_path = os.path.join(settings.BASE_DIR, 'test_dummy_dir')
    os.mkdir(self.dummy_src_path)
    copy_local_resource(
        os.path.join(TESTDIR, 'valid_operation.json'), 
        os.path.join(self.dummy_src_path, settings.OPERATION_SPEC_FILENAME)
    )

    mock_clone_repository.return_value = self.dummy_src_path
    mock_retrieve_commit_hash.return_value = 'abcde'

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