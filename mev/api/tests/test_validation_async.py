import unittest
import unittest.mock as mock
import uuid
import os

from django.core.exceptions import ImproperlyConfigured
from django.contrib.auth import get_user_model

from exceptions import ResourceValidationException, \
    NoResourceFoundException
from constants import TSV_FORMAT, \
    INTEGER_MATRIX_KEY

from api.async_tasks.async_resource_tasks import validate_resource
from api.models import Resource
        
from api.tests.base import BaseAPITestCase

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
    @mock.patch('api.async_tasks.async_resource_tasks.default_storage')
    def test_validation_exception_handled(self, \
        mock_default_storage, \
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
        mock_alert_admins.assert_called()
        self.assertTrue(r.status == Resource.UNEXPECTED_VALIDATION_ERROR)
        mock_default_storage.copy_to_storage.assert_called()
