import unittest
import unittest.mock as mock
import uuid
import random
import os

from django.core.exceptions import ImproperlyConfigured
from django.contrib.auth import get_user_model

from api.exceptions import ResourceValidationException
from api.async_tasks.async_resource_tasks import validate_resource, validate_resource_and_store
from api.models import Resource, ResourceMetadata
from resource_types.base import DataResource
from resource_types import RESOURCE_MAPPING, IntegerMatrix

from constants import DB_RESOURCE_KEY_TO_HUMAN_READABLE, \
    OBSERVATION_SET_KEY, \
    FEATURE_SET_KEY, \
    PARENT_OP_KEY, \
    RESOURCE_KEY, \
    TSV_FORMAT, \
    INTEGER_MATRIX_KEY
        
from api.utilities.resource_utilities import handle_valid_resource
from api.tests.base import BaseAPITestCase
from resource_types import get_resource_type_instance

from api.exceptions import NoResourceFoundException

# the api/tests dir
TESTDIR = os.path.dirname(__file__)
TESTDIR = os.path.join(TESTDIR, 'resource_validation_test_files')

class TestValidateResource(BaseAPITestCase):
    '''
    This tests that the proper things happen when we 
    call the asynchronous function to validate a Resource

    The actual validation and file relocation is mocked out
    but we check that the proper database objects are updated
    '''

    def setUp(self):
        self.establish_clients()

    def test_unknown_resource_id_raises_exception(self):
        '''
        If someone how an unknown resource UUID is passed to 
        the async validation function, raise an exception.

        Very unlikely, as the only "entry" to this method
        occurs directly after creating a valid Resource
        '''
        with self.assertRaises(NoResourceFoundException):
            junk_uuid = uuid.uuid4()
            validate_resource(junk_uuid, INTEGER_MATRIX_KEY, TSV_FORMAT)

    @mock.patch('api.async_tasks.async_resource_tasks.resource_utilities')
    @mock.patch('api.async_tasks.async_resource_tasks.alert_admins')
    def test_exception_handled(self, \
        mock_alert_admins, \
        mock_resource_utilities):
        '''
        If a general/unexpected exception is raised by the validation function, we 
        need to catch it and report to admins
        '''
        all_resources = Resource.objects.all()
        r = all_resources[0]
        initial_resource_type = r.resource_type
        mock_resource_utilities.get_resource_by_pk.return_value = r
        mock_resource_utilities.initiate_resource_validation.side_effect = [
            ResourceValidationException('xyz!!')]


        validate_resource(r.pk, 'ABC', TSV_FORMAT)
        mock_alert_admins.assert_not_called()
        r = Resource.objects.get(pk=r.pk)
        self.assertTrue(r.status == 'xyz!!')
        self.assertTrue(r.is_active)
        self.assertEqual(r.resource_type, initial_resource_type)

    @mock.patch('api.async_tasks.async_resource_tasks.resource_utilities')
    @mock.patch('api.async_tasks.async_resource_tasks.alert_admins')
    def test_validation_exception_handled(self, \
        mock_alert_admins, \
        mock_resource_utilities):
        '''
        If a predictable validation error occurs, we set the appropriate status
        '''
        all_resources = Resource.objects.all()
        r = all_resources[0]
        mock_resource_utilities.get_resource_by_pk.return_value = r
        mock_resource_utilities.initiate_resource_validation.side_effect = [Exception('ex!')]

        validate_resource(r.pk, 'ABC', TSV_FORMAT)
        mock_alert_admins.assert_called_with('ex!')
        self.assertTrue(r.status == 'ex!')