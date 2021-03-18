import uuid
import os
import json
import unittest.mock as mock

from django.urls import reverse
from django.core.exceptions import ImproperlyConfigured
from rest_framework import status
from rest_framework.exceptions import ValidationError
from django.conf import settings

from api.models import Resource
from api.tests.base import BaseAPITestCase
from api.tests import test_settings


class ResourceDownloadTests(BaseAPITestCase):

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
        if len(active_resources) == 0:
            raise ImproperlyConfigured('Need at least one active resource.')
        if len(inactive_resources) == 0:
            raise ImproperlyConfigured('Need at least one INactive resource.')
        # grab the first:
        self.active_resource = active_resources[0]
        self.inactive_resource = inactive_resources[0]

        self.url_for_active_resource = reverse(
            'download-resource', 
            kwargs={'pk':self.active_resource.pk}
        )
        self.url_for_inactive_resource = reverse(
            'download-resource', 
            kwargs={'pk':self.inactive_resource.pk}
        )

    def test_requires_auth(self):
        """
        Test that general requests to the endpoint generate 401
        """
        response = self.regular_client.get(self.url_for_active_resource)
        self.assertTrue((response.status_code == status.HTTP_401_UNAUTHORIZED) 
        | (response.status_code == status.HTTP_403_FORBIDDEN))

    @mock.patch('api.views.resource_download.get_storage_backend')
    def test_local_resource(self, mock_get_storage_backend):
        '''
        Tests the case where we have a local storage backend. Ensure
        that the response is as expected.
        '''
        mock_backend = mock.MagicMock()

        # an actual file
        f = os.path.join(self.TESTDIR, 'demo_file2.tsv')
        self.assertTrue(os.path.exists(f))
        mock_backend.get_download_url.return_value = f
        mock_backend.is_local_storage = True

        mock_get_storage_backend.return_value = mock_backend
        response = self.authenticated_regular_client.get(self.url_for_active_resource)
        self.assertEqual(response.status_code, 
            status.HTTP_200_OK)
        headers = response._headers
        content_type = headers['content-type']
        content_disp = headers['content-disposition']
        self.assertEqual(content_type, ('Content-Type', 'text/tab-separated-values'))
        self.assertEqual(content_disp, ('Content-Disposition', 'attachment; filename=demo_file2.tsv'))

    @mock.patch('api.views.resource_download.get_storage_backend')
    def test_remote_resource(self, mock_get_storage_backend):
        '''
        Tests the case where we have a remote storage backend. Ensure
        that the response is as expected.
        '''
        mock_backend = mock.MagicMock()
        some_url = 'https://some-remote-url/object.txt'
        mock_backend.get_download_url.return_value = some_url
        mock_backend.is_local_storage = False

        mock_get_storage_backend.return_value = mock_backend
        response = self.authenticated_regular_client.get(self.url_for_active_resource)
        self.assertTrue(response.status_code, status.HTTP_302_FOUND)
        headers = response._headers
        self.assertEqual(headers['location'], ('Location', some_url))

    def test_inactive_resource_request_returns_400(self):
        '''
        Tests the case where we have an inactive resource and a download request
        is issued. Should get a 400
        '''
        response = self.authenticated_regular_client.get(self.url_for_inactive_resource)
        self.assertTrue(response.status_code, status.HTTP_400_BAD_REQUEST)