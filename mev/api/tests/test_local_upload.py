import os
import uuid
import unittest.mock as mock

from django.urls import reverse
from django.core.exceptions import ImproperlyConfigured
from rest_framework import status

from api.models import Resource

from api.tests.base import BaseAPITestCase
from api.tests import test_settings


class ServerLocalResourceUploadTests(BaseAPITestCase):

    def setUp(self):

        self.url = reverse('resource-upload')
        self.establish_clients()

    @mock.patch('api.uploaders.base.api_tasks')
    def upload_and_cleanup(self, payload, mock_api_tasks):
        '''
        Same functionality is used by multiple functions, so just
        keep it here
        '''

        # get the number of Resources before the request
        num_initial_resources = len(Resource.objects.all())

        response = self.authenticated_regular_client.post(
            self.url, 
            data=payload, 
            format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        j = response.json()

        # check that the validation async task was called
        if 'resource_type' in payload:
            mock_api_tasks.validate_resource_and_store.delay.assert_called_with(
                uuid.UUID(j['id']), payload['resource_type'])
        else:
            mock_api_tasks.validate_resource_and_store.delay.assert_called_with(
                uuid.UUID(j['id']), None)

        # assert that we have more Resources now:
        num_current_resources = len(Resource.objects.all())
        self.assertTrue((num_current_resources - num_initial_resources) == 1)

        # validate that the Resource is created as expected
        j = response.json()
        r = Resource.objects.get(pk=j['id'])
        self.assertFalse(r.is_active)
        if 'is_public' in payload:
            self.assertTrue(payload['is_public'] == r.is_public)

        # cleanup:
        path = r.path
        self.assertTrue(os.path.exists(path))
        os.remove(path)

    def test_upload_requires_auth(self):
        '''
        Test that unauthenticated requests to the endpoint generate 401
        '''
        response = self.regular_client.get(self.url)
        self.assertTrue((response.status_code == status.HTTP_401_UNAUTHORIZED) 
        | (response.status_code == status.HTTP_403_FORBIDDEN))


    @mock.patch('api.serializers.resource.api_tasks')
    def test_missing_owner_is_ok(self, mock_api_tasks):
        '''
        Test that a request without an `owner`
        key is OK and the upload assigns to the 
        requesting user
        '''

        payload = {
            'resource_type': 'MTX',
            'upload_file': open(test_settings.TEST_UPLOAD, 'rb')
        }

        self.upload_and_cleanup(payload)


    @mock.patch('api.serializers.resource.api_tasks')
    def test_missing_resource_type_is_ok(self, mock_api_tasks):
        '''
        Missing the `resource_type` is OK- it's just set to None
        '''
        payload = {
            'owner_email': self.regular_user_1.email,
            'upload_file': open(test_settings.TEST_UPLOAD, 'rb')
        }

        self.upload_and_cleanup(payload)

        
    def test_incorrect_resource_type_raises_ex(self):
        '''
        The request contained the proper keys, but the
        `resource_type` key was not one of the valid types
        '''
        payload = {
            'owner_email': self.regular_user_1.email,
            'resource_type': 'AAAAAAAAAA',
            'upload_file': open(test_settings.TEST_UPLOAD, 'rb')
        }
        response = self.authenticated_regular_client.post(
            self.url, 
            data=payload, 
            format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @mock.patch('api.serializers.resource.api_tasks')
    def test_proper_upload_creates_pending_resource(self, mock_api_tasks):
        '''
        Test that we add a `Resource` to the database when a proper
        upload is initiated.

        Also check that the background async validation function
        is called
        '''
        payload = {
            'owner_email': self.regular_user_1.email,
            'resource_type': 'MTX',
            'upload_file': open(test_settings.TEST_UPLOAD, 'rb')
        }

        self.upload_and_cleanup(payload)


    @mock.patch('api.serializers.resource.api_tasks')
    def test_bad_owner_email_raises_ex(self, mock_api_tasks):
        '''
        Test that a bad email will raise an exception.  Everything else
        about the request is fine.
        '''
        # first check that the payload is correct by initiating a correct
        # request 
        payload = {
            'owner_email': self.regular_user_1.email,
            'resource_type': 'MTX',
            'upload_file': open(test_settings.TEST_UPLOAD, 'rb')
        }

        self.upload_and_cleanup(payload)

        # ok, now edit the owner_email field so that it's bad:
        payload = {
            'owner_email': test_settings.JUNK_EMAIL,
            'resource_type': 'MTX',
            'upload_file': open(test_settings.TEST_UPLOAD, 'rb')
        }
        response = self.authenticated_regular_client.post(
            self.url, 
            data=payload, 
            format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @mock.patch('api.serializers.resource.api_tasks')
    def test_cannot_upload_for_other_user(self, mock_api_tasks):
        '''
        Test that trying to upload a Resource for another user fails
        '''
        # first check that the payload is correct by initiating a correct
        # request 
        payload = {
            'owner_email': self.regular_user_1.email,
            'resource_type': 'MTX',
            'upload_file': open(test_settings.TEST_UPLOAD, 'rb')
        }

        self.upload_and_cleanup(payload)

        # ok, now edit the owner_email field so that it's someone else:
        payload = {
            'owner_email': self.regular_user_2.email,
            'resource_type': 'MTX',
            'upload_file': open(test_settings.TEST_UPLOAD, 'rb')
        }        
        response = self.authenticated_regular_client.post(
            self.url, 
            data=payload, 
            format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

class ServerLocalResourceUploadProgressTests(BaseAPITestCase):

    def setUp(self):

        self.url = reverse('resource-upload-progress')
        self.establish_clients()

    def test_missing_key_returns_error(self):
        '''
        Test that a request to the progress endpoint
        results in a 400.
        '''
        response = self.authenticated_regular_client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @mock.patch('api.views.resource_upload_views.cache')
    def test_payload_returned_with_proper_request(self, mock_cache):
        '''
        Test that we receive a proper JSON object indicating
        the upload progress.
        '''
        d = {'abc': 123}
        mock_cache.get.return_value = d

        # when a "real" client makes the request, the headers will have
        # "X-Progress-ID" which ends up being mutated to the string below:
        headers = {'HTTP_X_PROGRESS_ID': 'something'}

        response = self.authenticated_regular_client.get(self.url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), d)
