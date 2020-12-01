import os
import uuid
import unittest.mock as mock

from django.urls import reverse
from django.core.exceptions import ImproperlyConfigured
from rest_framework import status

from api.tests.base import BaseAPITestCase
from api.tests import test_settings


class LocalDropboxUploadTests(BaseAPITestCase):

    def setUp(self):
        self.url = reverse('dropbox-upload')
        self.establish_clients()

    def test_x(self):
        payload1 = {
            'download_link': 'https://dropbox-url.com/foo',
            'filename': 'abc'
        }
        payload2 = {
            'download_link': 'https://dropbox-url.com/bar',
            'filename': 'xyz'
        }
        response = self.authenticated_regular_client.post(
            self.url, 
            data=[payload1, payload2],
            format='json'
        )
        print(response.json())
        self.assertEqual(response.status_code, status.HTTP_200_OK)

class RemoteDropboxUploadTests(BaseAPITestCase):
    def setUp(self):
        self.url = reverse('dropbox-upload')
        self.establish_clients()

    def test_x(self):
        print('here, remote')