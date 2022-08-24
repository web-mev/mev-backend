import unittest
import unittest.mock as mock

from django.core.exceptions import ImproperlyConfigured

from api.models import Resource
from api.tests.base import BaseAPITestCase

class TestAsyncResourceTasks(BaseAPITestCase):
    '''
    This tests async functions that are related to Resource instances.
    '''

    def setUp(self):
        pass
