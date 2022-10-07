import os
import uuid
import unittest.mock as mock

from django.conf import settings
from django.urls import reverse
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import default_storage
from rest_framework import status
from rest_framework.exceptions import ValidationError, APIException

from constants import TSV_FORMAT
from api.models import Resource

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
        resource.datafile.delete()

    def upload(self, 
        payload, 
        client):
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

        # assert that we have more Resources now:
        num_current_resources = len(Resource.objects.all())
        self.assertTrue((num_current_resources - num_initial_resources) == 1)

        # validate that the Resource is created as expected
        j = response.json()
        self.assertTrue(j['is_active'])
        return j

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
            'datafile': open(self.test_upload, 'rb')
        }

        j = self.upload(payload, self.authenticated_regular_client)
        r = Resource.objects.get(pk=j['id'])
        self.assertTrue(r.owner == self.regular_user_1)
        self.cleanup(r)

    def test_file_placed_in_owner_dir(self):
        '''
        Test that a request properly places the file in the 
        owner-associated directory
        '''
        payload = {
            'datafile': open(self.test_upload, 'rb')
        }

        j = self.upload(payload, self.authenticated_regular_client)
        r = Resource.objects.get(pk=j['id'])
        self.assertTrue(r.owner == self.regular_user_1)
        print(self.regular_user_1.pk)
        self.assertEqual(
            os.path.dirname(r.datafile.name),
            str(self.regular_user_1.pk)   
        )
        self.cleanup(r)

    def test_file_size_saved(self):
        '''
        Test that a request properly places the file in the 
        owner-associated directory
        '''
        payload = {
            'datafile': open(self.test_upload, 'rb')
        }
        expected_size = os.path.getsize(self.test_upload)

        j = self.upload(payload, self.authenticated_regular_client)
        r = Resource.objects.get(pk=j['id'])
        self.assertEqual(j['size'], expected_size)
        self.assertEqual(r.size, expected_size)        
        self.cleanup(r)

    def test_uploaded_filename_with_space(self):
        '''
        Test that files with spaces are modified and the corresponding
        name is edited.
        '''
        orig_name = 'test name with spaces.tsv'
        payload = {
            'datafile': open(os.path.join(TESTDIR, self.upload_test_dir, orig_name), 'rb')
        }
        j = self.upload(payload, self.authenticated_regular_client)
        r = Resource.objects.get(pk=j['id'])
        self.assertTrue(r.owner == self.regular_user_1)
        modified_name = orig_name.replace(' ', '_')
        self.assertTrue(r.name == modified_name)
        self.assertIsNone(r.file_format) # was not set upon upload
        self.cleanup(r)

    def test_uploaded_file_with_atypical_and_non_ascii_name_is_handled(self):
        '''
        Test that we properly handle a file name that has different characters.
        Recall that the filename is just a string
        '''
        # This path is not valid, so it and the name will be changed
        filename = '?5x.tsv'
        corrected_name = '5x.tsv'
        payload = {
            'datafile': open(os.path.join(TESTDIR, self.upload_test_dir, filename), 'rb')
        }
        j = self.upload(payload, self.authenticated_regular_client)
        r = Resource.objects.get(pk=j['id'])
        self.assertEqual(r.name, corrected_name)
        # the upload has not set a file format, so that is just an empty string
        self.assertIsNone(r.file_format, None)
        self.cleanup(r)

        # try a name with a unicode char:
        char = 'ゑ'
        filename = char + '.tsv'
        payload = {
            'datafile': open(os.path.join(TESTDIR, self.upload_test_dir, filename), 'rb')
        }
        j = self.upload(payload, self.authenticated_regular_client)
        r = Resource.objects.get(pk=j['id'])
        self.assertEqual(r.name, filename)
        self.cleanup(r)

    def test_no_overwrite_upon_upload(self):
        '''
        Test that the storage system is setup so that repeated uploads do 
        NOT overwrite.
        '''
        char = 'ゑ'
        filename = char + '.tsv'
        payload = {
            'datafile': open(os.path.join(TESTDIR, self.upload_test_dir, filename), 'rb')
        }
        j1 = self.upload(payload, self.authenticated_regular_client)
        r1 = Resource.objects.get(pk=j1['id'])
        self.assertEqual(r1.name, filename)

        # Note that we don't clean up yet.

        # Now issue the same request again. It should create a second file with a unique name
        payload = {
            'datafile': open(os.path.join(TESTDIR, self.upload_test_dir, filename), 'rb')
        }
        j2 = self.upload(payload, self.authenticated_regular_client)
        r2 = Resource.objects.get(pk=j2['id'])
        # the name has changed
        self.assertFalse(r2.name == filename)
        self.assertTrue(r1.name != r2.name)

        contents1 = r1.datafile.read()
        contents2 = r2.datafile.read()
        self.assertEqual(contents1, contents2)

        self.cleanup(r1)
        self.cleanup(r2)