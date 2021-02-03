import os
import uuid
import unittest.mock as mock

from django.urls import reverse
from django.core.exceptions import ImproperlyConfigured
from rest_framework import status
from rest_framework.exceptions import ValidationError

from api.models import Resource
from api.utilities import normalize_identifier

from api.tests.base import BaseAPITestCase
from api.tests import test_settings

TESTDIR = os.path.dirname(__file__)

class ServerLocalResourceUploadTests(BaseAPITestCase):

    def setUp(self):

        self.url = reverse('resource-upload')
        self.establish_clients()

    def cleanup(self, resource):
        self.assertFalse(resource.is_active)
        path = resource.path
        self.assertTrue(os.path.exists(path))
        os.remove(path)

    @mock.patch('api.uploaders.base.validate_resource_and_store')
    def upload_and_cleanup(self, 
        payload, 
        client,
        mock_validate_resource_and_store):
        '''
        Same functionality is used by multiple functions, so just
        keep it here
        '''

        # get the number of Resources before the request
        num_initial_resources = len(Resource.objects.all())

        response = client.post(
            self.url, 
            data=payload, 
            format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        j = response.json()

        # check that the validation async task was called
        if 'resource_type' in payload:
            mock_validate_resource_and_store.delay.assert_called_with(
                uuid.UUID(j['id']), payload['resource_type'])
        else:
            mock_validate_resource_and_store.delay.assert_called_with(
                uuid.UUID(j['id']), None)

        # assert that we have more Resources now:
        num_current_resources = len(Resource.objects.all())
        self.assertTrue((num_current_resources - num_initial_resources) == 1)

        # validate that the Resource is created as expected
        j = response.json()
        r = Resource.objects.get(pk=j['id'])
        self.cleanup(r)
        return r

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

        r = self.upload_and_cleanup(payload, self.authenticated_regular_client)
        self.assertTrue(r.owner == self.regular_user_1)

    @mock.patch('api.serializers.resource.api_tasks')
    def test_owner_is_empty_string(self, mock_api_tasks):
        '''
        Test that a request with `owner`
        key as an emtpy string is OK and the upload assigns to the 
        requesting user
        '''

        payload = {
            'owner_email':'',
            'resource_type': 'MTX',
            'upload_file': open(test_settings.TEST_UPLOAD, 'rb')
        }

        r = self.upload_and_cleanup(payload, self.authenticated_regular_client)
        self.assertTrue(r.owner == self.regular_user_1)

    @mock.patch('api.serializers.resource.api_tasks')
    def test_missing_resource_type_is_ok(self, mock_api_tasks):
        '''
        Missing the `resource_type` is OK- it's just set to None
        '''
        payload = {
            'owner_email': self.regular_user_1.email,
            'upload_file': open(test_settings.TEST_UPLOAD, 'rb')
        }

        self.upload_and_cleanup(payload, self.authenticated_regular_client)

        
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

        self.upload_and_cleanup(payload, self.authenticated_regular_client)


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
        r = self.upload_and_cleanup(payload, self.authenticated_regular_client)
        self.assertTrue(r.owner == self.regular_user_1)

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
        r = self.upload_and_cleanup(payload, self.authenticated_regular_client)
        self.assertTrue(r.owner == self.regular_user_1)

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

    @mock.patch('api.serializers.resource.api_tasks')
    def test_owner_and_ownerless_conflict(self, mock_api_tasks):
        '''
        In this test, we are uploading as a "regular" user. They can't set 
        the private/public status
        '''
        payload = {
            'owner_email': self.admin_user.email,
            'resource_type': 'MTX',
            'upload_file': open(test_settings.TEST_UPLOAD, 'rb'),
            'is_ownerless': True
        }

        response = self.authenticated_admin_client.post(
            self.url, 
            data=payload, 
            format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @mock.patch('api.serializers.resource.api_tasks')
    def test_ownerless_by_regular_user(self, mock_api_tasks):
        '''
        In this test, we are uploading as a "regular" user. They can't set 
        a resource to ownerless
        '''
        # first check that the payload is correct by initiating a correct
        # request 
        payload = {
            'resource_type': 'MTX',
            'upload_file': open(test_settings.TEST_UPLOAD, 'rb'),
            'is_ownerless': True
        }

        response = self.authenticated_regular_client.post(
            self.url, 
            data=payload, 
            format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @mock.patch('api.serializers.resource.api_tasks')
    def test_ownerless_by_admin_user(self, mock_api_tasks):
        '''
        admin users can set an upload to be ownerless
        '''
        # first check that the payload is correct by initiating a correct
        # request 
        payload = {
            'resource_type': 'MTX',
            'upload_file': open(test_settings.TEST_UPLOAD, 'rb'),
            'is_ownerless': True
        }

        response = self.authenticated_admin_client.post(
            self.url, 
            data=payload, 
            format='multipart'
        )
        j = response.json()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        r = Resource.objects.get(pk=j['id'])
        self.cleanup(r)

    @mock.patch('api.serializers.resource.api_tasks')
    def test_cannot_set_public_status(self, mock_api_tasks):
        '''
        In this test, we are uploading as a "regular" user. They can't set 
        the private/public status
        '''
        # first check that the payload is correct by initiating a correct
        # request 
        payload = {
            'owner_email': self.regular_user_1.email,
            'resource_type': 'MTX',
            'is_public': False,
            'upload_file': open(test_settings.TEST_UPLOAD, 'rb')
        }
        r = self.upload_and_cleanup(payload, self.authenticated_regular_client)
        self.assertTrue(r.owner == self.regular_user_1)

        payload = {
            'owner_email': self.regular_user_1.email,
            'resource_type': 'MTX',
            'is_public': True,
            'upload_file': open(test_settings.TEST_UPLOAD, 'rb')
        }
        response = self.authenticated_regular_client.post(
            self.url, 
            data=payload, 
            format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @mock.patch('api.serializers.resource.api_tasks')
    def test_admin_can_set_public_status(self, mock_api_tasks):
        '''
        Test that admins can upload and set a file to be public.
        Used for exposing common files that many users would be using, 
        such as a pathway files, etc.

        One tricky issue is that admins can also act as "regular" users in the 
        sense that they can run analyses and have private files. To prevent admin
        users can inadvertedly exposing their own files, one has to specifically request
        a null owner if they set is_public to true.
        '''

        # even admins need to explicitly send 'is_ownerless'
        # to set a resource to public
        payload = {
            'resource_type': 'MTX',
            'is_public': True,
            'upload_file': open(test_settings.TEST_UPLOAD, 'rb')
        }
        response = self.authenticated_admin_client.post(
            self.url, 
            data=payload, 
            format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # to set it to a public Resource, we have to explicitly pass
        # is_ownerless
        payload = {
            #'owner_email': None,
            'resource_type': 'MTX',
            'is_public': True,
            'is_ownerless': True,
            'upload_file': open(test_settings.TEST_UPLOAD, 'rb')
        }
        response = self.authenticated_admin_client.post(
            self.url, 
            data=payload, 
            format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        j = response.json()
        r = Resource.objects.get(pk=j['id'])
        self.assertTrue(r.is_public)
        self.assertIsNone(r.owner)

        # to set it to a public Resource, we have to explicitly pass
        # is_ownerless
        payload = {
            'owner_email': '',
            'resource_type': 'MTX',
            'is_public': True,
            'is_ownerless': True,
            'upload_file': open(test_settings.TEST_UPLOAD, 'rb')
        }
        response = self.authenticated_admin_client.post(
            self.url, 
            data=payload, 
            format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        j = response.json()
        r = Resource.objects.get(pk=j['id'])
        self.assertTrue(r.is_public)
        self.assertIsNone(r.owner)

    @mock.patch('api.serializers.resource.api_tasks')
    def test_uploaded_filename_is_normalized(self, mock_api_tasks):
        '''
        Test that we properly normalize file names that are 'out of bounds'
        (e.g. we edit the filename to be easy to handle)
        '''
        # first check that the payload is correct by initiating a correct
        # request 
        orig_name = 'test name with spaces.tsv'
        edited_name = normalize_identifier(orig_name)
        payload = {
            'owner_email': self.regular_user_1.email,
            'resource_type': 'MTX',
            'upload_file': open(os.path.join(TESTDIR, orig_name), 'rb')
        }
        r = self.upload_and_cleanup(payload, self.authenticated_regular_client)
        self.assertTrue(r.owner == self.regular_user_1)
        self.assertTrue(r.name == edited_name)
        # the full 'temporary filename is {uuid}.{basename}. The uuid is random,
        # so we can't compare the full basename
        s = '.'.join(os.path.basename(r.path).split('.')[1:])
        self.assertEqual(s, edited_name)

        # ok, now edit 


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
