import uuid
import unittest.mock as mock
import shutil
import json
import os

from django.urls import reverse
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from rest_framework import status

from api.models import Operation
from api.tests.base import BaseAPITestCase
from api.tests import test_settings
from api.utilities.basic_utils import copy_local_resource
from api.utilities.ingest_operation import perform_operation_ingestion

TESTDIR = os.path.dirname(__file__)
TESTDIR = os.path.join(TESTDIR, 'operation_test_files')

class OperationListTests(BaseAPITestCase):

    def setUp(self):

        self.url = reverse('operation-list')
        self.establish_clients()


    def test_list_operations_requires_auth(self):
        """
        Test that general requests to the endpoint generate 401
        """
        response = self.regular_client.get(self.url)
        self.assertTrue((response.status_code == status.HTTP_401_UNAUTHORIZED) 
        | (response.status_code == status.HTTP_403_FORBIDDEN))
    

    def test_inconsistent_db_and_dir(self):
        '''
        If (somehow) a directory containing an operation was removed,
        assure that we handle it well.
        '''
        # create an Operation instance that does NOT have a corresponding folder
        u = uuid.uuid4()
        Operation.objects.create(id=u, name='foo')

        # get all initial instances before anything happens:
        response = self.authenticated_regular_client.get(self.url, format='json')
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class OperationDetailTests(BaseAPITestCase):

    @mock.patch('api.utilities.ingest_operation.retrieve_commit_hash')
    @mock.patch('api.utilities.ingest_operation.clone_repository')
    def setUp(self, mock_clone_repository, mock_retrieve_commit_hash):

        # make a dummy git repo:
        self.dummy_src_path = os.path.join(settings.BASE_DIR, 'test_dummy_dir')
        os.mkdir(self.dummy_src_path)
        copy_local_resource(
            os.path.join(TESTDIR, 'valid_operation.json'), 
            os.path.join(self.dummy_src_path, settings.OPERATION_SPEC_FILENAME)
        )

        mock_clone_repository.return_value = self.dummy_src_path
        mock_retrieve_commit_hash.return_value = 'abcde'

        # create a valid operation folder and database object:
        u = perform_operation_ingestion('http://github.com/some-dummy-repo/')

        self.url = reverse('operation-detail', kwargs={
            'operation_uuid': str(u)
        })
        self.establish_clients()

    def tearDown(self):
        shutil.rmtree(self.dummy_src_path)

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
        u = uuid.uuid4()
        Operation.objects.create(id=u, name='foo')

        # query the other 'new' instance which has a database inconsistency:
        url = reverse('operation-detail', kwargs={
            'operation_uuid': str(u)
        })
        response = self.authenticated_regular_client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


    def test_unknown_operation_returns_404(self):
        
        unknown_uuid = uuid.uuid4()
        url = reverse('operation-detail', kwargs={
            'operation_uuid': str(unknown_uuid)
        })
        response = self.authenticated_regular_client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
