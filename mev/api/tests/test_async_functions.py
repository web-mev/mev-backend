import unittest
import unittest.mock as mock

from django.core.exceptions import ImproperlyConfigured

from api.models import Resource
from api.async_tasks.async_resource_tasks import store_resource

from api.tests.base import BaseAPITestCase

class TestAsyncResourceTasks(BaseAPITestCase):
    '''
    This tests async functions that are related to Resource instances.
    '''

    def setUp(self):
        pass

    @mock.patch('api.async_tasks.async_resource_tasks.resource_utilities')
    def test_async_storage_success(self, \
        mock_resource_utilities):
        '''
        Test that the async storage method sets the proper fields on the 
        Resource instance.
        '''
        inactive_resources = Resource.objects.filter(is_active=False)
        if len(inactive_resources) == 0:
            raise ImproperlyConfigured('Need at least one inactive'
                ' Resource instance to run this test.')

        r = inactive_resources[0]
        mock_final_path = '/some/final/path.txt'
        mock_resource_utilities.get_resource_by_pk.return_value = r
        mock_resource_utilities.move_resource_to_final_location.return_value = mock_final_path
        store_resource(str(r.pk))
        self.assertTrue(r.path == mock_final_path)
        self.assertTrue(r.is_active)
        self.assertTrue(r.status == Resource.READY)

    @mock.patch('api.async_tasks.async_resource_tasks.resource_utilities')
    def test_async_storage_failure(self, \
        mock_resource_utilities):
        '''
        Test that the async storage method sets the proper fields on the 
        Resource instance. Here, we mock there being a storage failure
        '''
        inactive_resources = Resource.objects.filter(is_active=False)
        if len(inactive_resources) == 0:
            raise ImproperlyConfigured('Need at least one inactive'
                ' Resource instance to run this test.')

        r = inactive_resources[0]
        initial_path = r.path
        mock_resource_utilities.get_resource_by_pk.return_value = r
        mock_resource_utilities.move_resource_to_final_location.side_effect = Exception('ack!')
        store_resource(str(r.pk))
        self.assertTrue(r.path == initial_path)
        self.assertTrue(r.is_active)
        self.assertTrue(r.status == Resource.UNEXPECTED_STORAGE_ERROR)
