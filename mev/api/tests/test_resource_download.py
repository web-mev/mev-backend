from io import BytesIO
import uuid
import os
import json
import unittest.mock as mock

from django.urls import reverse
from django.core.exceptions import ImproperlyConfigured
from rest_framework import status
from rest_framework.exceptions import ValidationError
from django.conf import settings
from django.core.files import File

from api.models import Resource
from api.tests.base import BaseAPITestCase
from api.tests import test_settings
from api.tests.test_helpers import cleanup_resource_file, \
    associate_file_with_resource

class ResourceDownloadTests(BaseAPITestCase):
    '''
    Tests the direct downloads, as is the case when the storage backend is
    "local". 
    '''

    def setUp(self):

        self.establish_clients()

        self.TESTDIR = os.path.join(
            os.path.dirname(__file__),
            'resource_contents_test_files'    
        )

        # get an example from the database:
        regular_user_resources = Resource.objects.filter(
            owner=self.regular_user_1,
        )
        if len(regular_user_resources) == 0:
            msg = '''
                Testing not setup correctly.  Please ensure that there is at least one
                Resource instance for the user {user}
            '''.format(user=self.regular_user_1)
            raise ImproperlyConfigured(msg)

        active_resources = []
        inactive_resources = []
        for r in regular_user_resources:
            if r.is_active:
                active_resources.append(r)
            else:
                inactive_resources.append(r)

        active_resources_which_are_small_enough = [x for x in active_resources if x.size < settings.MAX_DOWNLOAD_SIZE_BYTES]
        active_resources_which_are_too_large = [x for x in active_resources if x.size > settings.MAX_DOWNLOAD_SIZE_BYTES]

        if len(active_resources) == 0:
            raise ImproperlyConfigured('Need at least one active resource.')
        if len(inactive_resources) == 0:
            raise ImproperlyConfigured('Need at least one INactive resource.')
        if len(active_resources_which_are_small_enough) == 0:
            raise ImproperlyConfigured('Need at least one active resource with a size smaller than %d.' % settings.MAX_DOWNLOAD_SIZE_BYTES)
        if len(active_resources_which_are_too_large) == 0:
            raise ImproperlyConfigured('Need at least one active resource with a size larger than %d.' % settings.MAX_DOWNLOAD_SIZE_BYTES)

        # get an active resource that is small enough to pass the download size threshold:
        self.small_active_resource = active_resources_which_are_small_enough[0]
        # and one that is too large (which we block)
        self.large_active_resource = active_resources_which_are_too_large[0]
        self.inactive_resource = inactive_resources[0]

        self.url_for_small_active_resource = reverse(
            'download-resource', 
            kwargs={'pk':self.small_active_resource.pk}
        )
        self.url_for_large_active_resource = reverse(
            'download-resource', 
            kwargs={'pk':self.large_active_resource.pk}
        )
        self.url_for_inactive_resource = reverse(
            'download-resource', 
            kwargs={'pk':self.inactive_resource.pk}
        )

    def test_requires_auth(self):
        """
        Test that general requests to the endpoint generate 401
        """
        response = self.regular_client.get(self.url_for_small_active_resource)
        self.assertTrue((response.status_code == status.HTTP_401_UNAUTHORIZED) 
        | (response.status_code == status.HTTP_403_FORBIDDEN))

    @mock.patch('api.views.resource_download.check_resource_request_validity')
    def test_local_resource_for_small_file(self, mock_check_resource_request_validity):
        '''
        Tests the case where we have a local storage backend and are requesting 
        the download of a file that is sufficiently small. Should proceed and
        send them back a file.
        '''

        # an actual file from which we get contents
        resource_path = os.path.join(self.TESTDIR, 'demo_file2.tsv')
        self.assertTrue(os.path.exists(resource_path))
        associate_file_with_resource(self.small_active_resource, resource_path)
        filename = self.small_active_resource.name
        mock_check_resource_request_validity.return_value = self.small_active_resource

        response = self.authenticated_regular_client.get(
            self.url_for_small_active_resource)
        self.assertEqual(response.status_code, 
            status.HTTP_200_OK)
        headers = response.headers
        content_type = headers['Content-Type']
        content_disp = headers['Content-Disposition']
        self.assertEqual(content_type, 'text/tab-separated-values')
        self.assertEqual(content_disp, f'attachment; filename="{filename}"')
        file_contents = open(resource_path, 'rb').read()
        self.assertEqual(file_contents, response.content)
        cleanup_resource_file(self.small_active_resource)

    @mock.patch('api.views.resource_download.check_resource_request_validity')
    def test_local_resource_for_large_file(self, mock_check_resource_request_validity):
        '''
        Tests the case where we have a local storage backend and a file is requested that
        is too large for our local download. Return 400 with a status message indicating
        that the file should be downloaded by another means (e.g. Dropbox, etc)
        '''

        mock_check_resource_request_validity.return_value = self.large_active_resource
        response = self.authenticated_regular_client.get(self.url_for_large_active_resource)
        self.assertEqual(response.status_code, 
            status.HTTP_400_BAD_REQUEST)

    def test_inactive_resource_request_returns_400(self):
        '''
        Tests the case where we have an inactive resource and a download request
        is issued. Should get a 400
        '''
        response = self.authenticated_regular_client.get(self.url_for_inactive_resource)
        self.assertTrue(response.status_code, status.HTTP_400_BAD_REQUEST)


class ResourceUrlFetchTests(BaseAPITestCase):
    '''
    Tests the endpoint that provides the download url, which is based on the backend storage
    service
    '''

    def setUp(self):

        self.establish_clients()

        self.TESTDIR = os.path.join(
            os.path.dirname(__file__),
            'resource_contents_test_files'    
        )

        # get an example from the database:
        regular_user_resources = Resource.objects.filter(
            owner=self.regular_user_1,
        )
        if len(regular_user_resources) == 0:
            msg = '''
                Testing not setup correctly.  Please ensure that there is at least one
                Resource instance for the user {user}
            '''.format(user=self.regular_user_1)
            raise ImproperlyConfigured(msg)

        active_resources = []
        inactive_resources = []
        for r in regular_user_resources:
            if r.is_active:
                active_resources.append(r)
            else:
                inactive_resources.append(r)

        active_resources_which_are_small_enough = [x for x in active_resources if x.size < settings.MAX_DOWNLOAD_SIZE_BYTES]
        active_resources_which_are_too_large = [x for x in active_resources if x.size > settings.MAX_DOWNLOAD_SIZE_BYTES]

        if len(active_resources) == 0:
            raise ImproperlyConfigured('Need at least one active resource.')
        if len(inactive_resources) == 0:
            raise ImproperlyConfigured('Need at least one INactive resource.')
        if len(active_resources_which_are_small_enough) == 0:
            raise ImproperlyConfigured('Need at least one active resource with a size smaller than %d.' % settings.MAX_DOWNLOAD_SIZE_BYTES)
        if len(active_resources_which_are_too_large) == 0:
            raise ImproperlyConfigured('Need at least one active resource with a size larger than %d.' % settings.MAX_DOWNLOAD_SIZE_BYTES)

        # get an active resource that is small enough to pass the download size threshold:
        self.small_active_resource = active_resources_which_are_small_enough[0]
        # and one that is too large (which we block)
        self.large_active_resource = active_resources_which_are_too_large[0]
        self.inactive_resource = inactive_resources[0]

        self.url_for_small_active_resource = reverse(
            'download-resource-url', 
            kwargs={'pk':self.small_active_resource.pk}
        )
        self.url_for_large_active_resource = reverse(
            'download-resource-url', 
            kwargs={'pk':self.large_active_resource.pk}
        )
        self.url_for_inactive_resource = reverse(
            'download-resource-url', 
            kwargs={'pk':self.inactive_resource.pk}
        )

    def test_requires_auth(self):
        """
        Test that general requests to the endpoint generate 401
        """
        response = self.regular_client.get(self.url_for_small_active_resource)
        self.assertTrue((response.status_code == status.HTTP_401_UNAUTHORIZED) 
        | (response.status_code == status.HTTP_403_FORBIDDEN))

    #TODO: re-write tests once 'direct from bucket' downloads are enabled.
    # @mock.patch('api.views.resource_download.check_resource_request_validity')
    # def test_local_resource_for_small_file(self, mock_check_resource_request_validity):
    #     '''
    #     Tests the case where we have a local storage backend and are requesting 
    #     the download of a file that is sufficiently small. Should proceed to give them
    #     a "proper" download url in the response
    #     '''
    #     # an actual file from which we get contents
    #     f = os.path.join(self.TESTDIR, 'demo_file2.tsv')
    #     self.assertTrue(os.path.exists(f))
    #     file_contents = open(f, 'rb').read()

    #     filename = 'some_tmp_file.tsv'
    #     # create a dummy/empty data file in storage
    #     r = Resource.objects.create(
    #         owner=self.regular_user_1,
    #         datafile=File(BytesIO(), filename),
    #         name=filename
    #     )
    #     # now write the file contents in there:
    #     with r.datafile.open('wb') as fout:
    #         fout.write(file_contents)
    #     url = reverse(
    #         'download-resource-url', 
    #         kwargs={'pk':r.pk}
    #     )
    #     mock_check_resource_request_validity.return_value = r

    #     response = self.authenticated_regular_client.get(url)
    #     self.assertEqual(response.status_code, 
    #         status.HTTP_200_OK)
    #     j = response.json()
    #     print(j)
    #     self.assertTrue(j['download_type'] == 'local')

    # @mock.patch('api.views.resource_download.get_storage_backend')
    # def test_local_resource_for_large_file(self, mock_get_storage_backend):
    #     '''
    #     Tests the case where we have a local storage backend and a file is requested that
    #     is too large for our local download. This should still return a 200 which provides
    #     a payload with the actual url for the download. We only check the file size if the
    #     user actually makes a request to the download endpoint. Recall that this is simply
    #     an endpoint that returns a url which depends on the storage backend
    #     '''
    #     mock_backend = mock.MagicMock()

    #     # an actual file
    #     f = os.path.join(self.TESTDIR, 'demo_file2.tsv')
    #     self.assertTrue(os.path.exists(f))
    #     mock_backend.get_download_url.return_value = f
    #     mock_backend.is_local_storage = True

    #     mock_get_storage_backend.return_value = mock_backend
    #     response = self.authenticated_regular_client.get(self.url_for_large_active_resource)
    #     self.assertEqual(response.status_code, 
    #         status.HTTP_200_OK)
    #     j = response.json()
    #     self.assertTrue(j['download_type'] == 'local')

    # @mock.patch('api.views.resource_download.get_storage_backend')
    # def test_remote_resource(self, mock_get_storage_backend):
    #     '''
    #     Tests the case where we have a remote storage backend. Ensure
    #     that the response is as expected.
    #     '''
    #     mock_backend = mock.MagicMock()
    #     some_url = 'https://some-remote-url/object.txt'
    #     mock_backend.get_download_url.return_value = some_url

    #     # this is what mocks us using a remote file storage service
    #     mock_backend.is_local_storage = False

    #     mock_get_storage_backend.return_value = mock_backend

    #     response = self.authenticated_regular_client.get(self.url_for_small_active_resource)
    #     self.assertTrue(response.status_code, status.HTTP_200_OK)
    #     j = response.json()
    #     self.assertTrue(j['download_type'] != 'local')
    #     self.assertTrue(j['url'] == some_url)

    #     # also test for a large file. Should not matter since the storage backend is remote.
    #     response = self.authenticated_regular_client.get(self.url_for_large_active_resource)
    #     self.assertTrue(response.status_code, status.HTTP_200_OK)
    #     j = response.json()
    #     self.assertTrue(j['download_type'] != 'local')
    #     self.assertTrue(j['url'] == some_url)

    # def test_inactive_resource_request_returns_400(self):
    #     '''
    #     Tests the case where we have an inactive resource and a download request
    #     is issued. Should get a 400
    #     '''
    #     response = self.authenticated_regular_client.get(self.url_for_inactive_resource)
    #     self.assertTrue(response.status_code, status.HTTP_400_BAD_REQUEST)
