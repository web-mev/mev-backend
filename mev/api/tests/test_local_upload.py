import os
import uuid
import unittest.mock as mock

from django.conf import settings
from django.urls import reverse
from django.core.exceptions import ImproperlyConfigured
from rest_framework import status
from rest_framework.exceptions import ValidationError, APIException

from constants import TSV_FORMAT
from api.models import Resource
from api.utilities import normalize_filename

from api.tests.base import BaseAPITestCase
from api.tests import test_settings

TESTDIR = os.path.dirname(__file__)

class ServerLocalResourceUploadTests(BaseAPITestCase):

    def setUp(self):

        self.url = reverse('resource-upload')
        self.establish_clients()
        self.test_upload = os.path.join(
            settings.BASE_DIR, 
            'api', 'tests', 'upload_test_files', 'test_upload.tsv')
        TEST_UPLOAD_WITH_INVALID_NAME = os.path.join(settings.BASE_DIR, 'api', 'tests', 'upload_test_files', '5x.tsv')
        self.upload_test_dir = 'upload_test_files' # relative to the testing dir

    def cleanup(self, resource):
        self.assertFalse(resource.is_active)
        path = resource.path
        self.assertTrue(os.path.exists(path))
        os.remove(path)

    @mock.patch('api.views.resource_upload_views.store_resource')
    def upload_and_cleanup(self, 
        payload, 
        client,
        mock_store):
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
        mock_store.delay.assert_called_with(
            uuid.UUID(j['id']))

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


    def test_owner_properly_assigned(self):
        '''
        Test that a request properly assigns the Resource to the 
        requesting user
        '''
        payload = {
            'upload_file': open(self.test_upload, 'rb')
        }

        r = self.upload_and_cleanup(payload, self.authenticated_regular_client)
        self.assertTrue(r.owner == self.regular_user_1)


    @mock.patch('api.serializers.resource.api_tasks')
    @mock.patch('api.uploaders.local_upload.uuid')
    def test_uploaded_filename_with_space(self, mock_uuid, mock_api_tasks):
        '''
        Test that files with spaces retain the name but the path is set to be UUID-based. 
        '''
        u = uuid.uuid4()
        mock_uuid.uuid4.return_value = u

        orig_name = 'test name with spaces.tsv'
        payload = {
            'upload_file': open(os.path.join(TESTDIR, self.upload_test_dir, orig_name), 'rb')
        }
        r = self.upload_and_cleanup(payload, self.authenticated_regular_client)
        self.assertTrue(r.owner == self.regular_user_1)
        self.assertTrue(r.name == orig_name)
        basename = os.path.basename(r.path)
        self.assertEqual(str(u), basename)
        self.assertEqual(u, r.pk)
        self.assertIsNone(r.file_format) # was not set upon upload


    @mock.patch('api.serializers.resource.api_tasks')
    @mock.patch('api.uploaders.local_upload.uuid')
    def test_uploaded_file_with_atypical_and_non_ascii_name_is_handled(self, mock_uuid, mock_api_tasks):
        '''
        Test that we properly handle a file name that has different characters.
        Recall that the filename is just a string
        '''
        u = uuid.uuid4()
        mock_uuid.uuid4.return_value = u

        filename = '?5x.tsv'
        payload = {
            'upload_file': open(os.path.join(TESTDIR, self.upload_test_dir, filename), 'rb')
        }
        r = self.upload_and_cleanup(payload, self.authenticated_regular_client)
        self.assertEqual(u, r.pk)
        resource_path = r.path
        basename = os.path.basename(resource_path)
        self.assertEqual(str(u), basename)
        self.assertEqual(r.name, filename)
        # the upload has not set a file format, so that is just an empty string
        self.assertIsNone(r.file_format, None)

        # try a name with a unicode char:
        u2 = uuid.uuid4()
        mock_uuid.uuid4.return_value = u2
        char = 'ゑ'
        filename = char + '.tsv'
        payload = {
            'upload_file': open(os.path.join(TESTDIR, self.upload_test_dir, filename), 'rb')
        }
        r = self.upload_and_cleanup(payload, self.authenticated_regular_client)

        self.assertEqual(u2, r.pk)
        resource_path = r.path
        basename = os.path.basename(resource_path)
        # this would raise an exception if it's not a UUID
        self.assertEqual(str(u2), basename)
        # double-check that the path does NOT contain that special char:
        self.assertFalse(char in resource_path)
        self.assertEqual(filename, r.name)
        # the upload has not set a file format, so that is just None
        self.assertIsNone(r.file_format)

    @mock.patch('api.views.resource_upload_views.ServerLocalResourceUpload.upload_handler_class')
    def test_api_exception_returns_500(self, mock_handler_class):
        '''
        Test the situation where the upload fails and the upload handler 
        raises an api exception
        '''
        mock_handler = mock.MagicMock()
        mock_handler.handle_upload.side_effect = APIException('oh no!')
        mock_handler_class.return_value = mock_handler

        payload = {
            'upload_file': open(self.test_upload, 'rb')
        }
        response = self.authenticated_regular_client.post(
            self.url, 
            data=payload, 
            format='multipart'
        )
        self.assertEqual(response.status_code, 500)

    @mock.patch('api.views.resource_upload_views.ServerLocalResourceUpload.upload_handler_class')
    def test_resource_create_failure_returns_500(self, mock_handler_class):
        '''
        Test the situation where the upload completes, but there is an unexpected
        issue when creating/saving the api.models.Resource instance
        '''
        mock_handler = mock.MagicMock()
        # If we are unable to create an instance of api.models.Resource in the 
        # api.uploaders.base.BaseUpload.create_resource_from_upload method,
        # it will return None:
        mock_handler.handle_upload.return_value = None
        mock_handler_class.return_value = mock_handler

        payload = {
            'upload_file': open(self.test_upload, 'rb')
        }
        response = self.authenticated_regular_client.post(
            self.url, 
            data=payload, 
            format='multipart'
        )
        self.assertEqual(response.status_code, 500)

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
