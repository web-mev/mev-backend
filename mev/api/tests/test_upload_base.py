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