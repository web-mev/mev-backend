import uuid
import os
import json
import unittest.mock as mock

from django.urls import reverse
from django.core.exceptions import ImproperlyConfigured
from rest_framework import status
from rest_framework.exceptions import ValidationError
from django.conf import settings


from api.models import Resource, Workspace
from resource_types import DATABASE_RESOURCE_TYPES, HUMAN_READABLE_TO_DB_STRINGS
from api.tests.base import BaseAPITestCase
from api.tests import test_settings


class ResourceTransformTests(BaseAPITestCase):

    def setUp(self):

        self.TESTDIR = os.path.join(
            os.path.dirname(__file__),
            'resource_contents_test_files'    
        )
        # get an example from the database:
        self.resource = Resource.objects.all()[0]
        
    def test_panda_subset_transform_case(self):
        fp = ''
        self.resource.path = fp