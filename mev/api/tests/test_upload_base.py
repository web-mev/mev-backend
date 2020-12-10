import os
import uuid
import unittest.mock as mock

from django.core.exceptions import ImproperlyConfigured
from rest_framework.exceptions import ValidationError
from rest_framework import status

from api.uploaders.base import BaseUpload

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

        # due to the endpoint being a multi-part, the
        # owner_email key needs to either be:
        # - absent
        # - empty string
        # - some email

        # first check empty string. Should responsd by returning the requester
        payload = {
            'owner_email': ''
        }
        o = b.check_request_and_owner(payload, mock_request)
        self.assertEqual(o, self.regular_user_1)

        # check payload lacking the key. should self-assign
        payload = {}
        o = b.check_request_and_owner(payload, mock_request)
        self.assertEqual(o, self.regular_user_1)

        # check email that correctly identifies themself
        payload = {
            'owner_email': self.regular_user_1.email
        }
        o = b.check_request_and_owner(payload, mock_request)
        self.assertEqual(o, self.regular_user_1)

        # check email of someone else 
        payload = {
            'owner_email': self.regular_user_2.email
        }
        with self.assertRaises(ValidationError):
            b.check_request_and_owner(payload, mock_request)
