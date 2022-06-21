import os
import uuid
import unittest.mock as mock

from django.core.exceptions import ImproperlyConfigured
from rest_framework.exceptions import ValidationError
from rest_framework import status

from api.uploaders.base import BaseUpload
from api.models import Resource

from api.tests.base import BaseAPITestCase
from api.tests import test_settings


class BaseUploadTests(BaseAPITestCase):
    def setUp(self):
        self.establish_clients()

    def test_request_and_owner_as_expected_from_regular_user_request(self):
        '''
        Ensures that the method works as expected when the request is initiated
        by a regular user.
        '''
        b = BaseUpload()

        mock_request = mock.MagicMock()
        mock_request.user = self.regular_user_1

        # check payload lacking the key. should return the 
        # requesting user.
        o = b.check_request_and_owner({}, mock_request)
        self.assertEqual(o, self.regular_user_1)

    def test_create_resource_from_upload(self):
        '''
        Tests that the `create_resource_from_upload` method does what it should...
        '''
        b = BaseUpload()

        mock_path = '/some/path'
        mock_name = 'some_name'
        mock_size = 100

        # set some attributes on that class that are set by other methods:
        u = uuid.uuid4()
        b.upload_resource_uuid = u
        b.owner = self.regular_user_1
        b.filepath = mock_path
        b.filename = mock_name
        b.is_public = False
        b.size = mock_size

        # count the original resources
        original_resources = Resource.objects.filter(owner=self.regular_user_1)
        n0 = len(original_resources)

        # call the method and check that we are returned a proper Resource instance.
        new_resource = b.create_resource_from_upload()
        final_resources = Resource.objects.filter(owner=self.regular_user_1)
        n1 = len(final_resources)
        self.assertTrue((n1-n0) ==1)
        self.assertEqual(new_resource.path, mock_path)
        self.assertEqual(new_resource.name, mock_name)
        self.assertEqual(new_resource.size, mock_size)

    @mock.patch('api.uploaders.base.ResourceSerializer')
    @mock.patch('api.uploaders.base.alert_admins')
    def test_create_resource_from_upload_failure(self, mock_alert_admins, \
        mock_resource_serializer_class):
        '''
        Tests that the `create_resource_from_upload` returns None and alerts
        the admins if something unexpected happens.
        '''
        b = BaseUpload()

        mock_path = '/some/path'
        mock_name = 'some_name'
        mock_size = 100

        # set some attributes on that class that are set by other methods:
        u = uuid.uuid4()
        b.upload_resource_uuid = u
        b.owner = self.regular_user_1
        b.filepath = mock_path
        b.filename = mock_name
        b.is_public = False
        b.size = mock_size

        # count the original Resource instances for this user.
        original_resources = Resource.objects.filter(owner=self.regular_user_1)
        n0 = len(original_resources)

        mock_resource_serializer_instance = mock.MagicMock()
        mock_resource_serializer_instance.is_valid.return_value = False
        mock_resource_serializer_class.return_value = mock_resource_serializer_instance

        # call the method
        new_resource = b.create_resource_from_upload()
        self.assertIsNone(new_resource)
        final_resources = Resource.objects.filter(owner=self.regular_user_1)
        n1 = len(final_resources)
        self.assertTrue((n1-n0) ==0)

        mock_alert_admins.assert_called()
        