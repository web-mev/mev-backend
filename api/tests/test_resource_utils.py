import os
import unittest
import unittest.mock as mock

from django.contrib.auth import get_user_model
from django.conf import settings

from rest_framework.exceptions import ValidationError

from api.models import Resource
from api.utilities.resource_utilities import create_resource_from_upload, \
    move_resource_to_final_location
from api.tests.base import BaseAPITestCase
from api.tests import test_settings

class TestResourceUtilities(BaseAPITestCase):
    '''
    Tests the functions contained in the api.utilities.resource_utilities
    module.
    '''
    def setUp(self):
        self.establish_clients()

    @mock.patch('api.serializers.resource.api_tasks')
    def test_invalid_resource_params_raises_ex(self, mock_api_tasks):

        num_original_resources = len(Resource.objects.all())

        # first check that a valid request works--
        filepath = '/a/b/c.txt'
        filename = 'foo.txt'
        resource_type = 'MTX'
        is_public = True
        is_local = True
        owner = self.regular_user_1

        r = create_resource_from_upload(filepath, 
            filename, 
            resource_type, 
            is_public,
            is_local,
            owner)

        mock_api_tasks.validate_resource.delay.assert_called()
  
        # check that we added a resource
        num_final_resources = len(Resource.objects.all())
        self.assertTrue((num_final_resources-num_original_resources) == 1)

        # check that the resource has what we expect:
        self.assertTrue(r.name == filename)
        self.assertTrue(r.is_public == is_public)
        self.assertFalse(r.is_active)
        self.assertIsNone(r.resource_type)

        # OK...now give it something bad and check that we catch an exception:
        with self.assertRaises(ValidationError):
            resource_type = 'JUNK'
            r = create_resource_from_upload(filepath, 
                filename, 
                resource_type, 
                is_public,
                is_local,
                owner)

    @mock.patch('api.utilities.resource_utilities.make_local_directory')
    @mock.patch('api.utilities.resource_utilities.move_resource')
    @mock.patch('api.utilities.resource_utilities.os.path.exists')
    def test_user_directory_created(self, mock_exists, mock_move_resource, mock_make_local_dir):
        '''
        Test that the final resource paths are setup correctly
        No files are actually moved-- all those functions are mocked out.
        '''
        owner = self.regular_user_1
        owner_resources = Resource.objects.filter(owner=owner)

        # pick one:
        owner_resource = owner_resources[0]
        owner_resource.is_local = True

        # mock the user directory not existing:
        mock_exists.return_value = False

        # make the call
        move_resource_to_final_location(owner_resource)

        expected_owner_directory = os.path.join(
            settings.USER_STORAGE_DIR,
            str(owner.user_uuid)
        )

        expected_filename = '%s.%s' % (str(owner_resource.pk), owner_resource.name)
        expected_final_path = os.path.join(expected_owner_directory, expected_filename)

        mock_make_local_dir.assert_called_with(expected_owner_directory)
        mock_move_resource.assert_called_with(owner_resource.path, expected_final_path)

    @mock.patch('api.utilities.resource_utilities.make_local_directory')
    @mock.patch('api.utilities.resource_utilities.move_resource')
    @mock.patch('api.utilities.resource_utilities.os.path.exists')
    def test_existing_user_directory(self, mock_exists, mock_move_resource, mock_make_local_dir):
        '''
        Test that the directory creation is skipped
        '''
        owner = self.regular_user_1
        owner_resources = Resource.objects.filter(owner=owner)

        # pick one:
        owner_resource = owner_resources[0]
        owner_resource.is_local = True

        # mock the user directory not existing:
        mock_exists.return_value = True

        # make the call
        move_resource_to_final_location(owner_resource)

        expected_owner_directory = os.path.join(
            settings.USER_STORAGE_DIR,
            str(owner.user_uuid)
        )

        expected_filename = '%s.%s' % (str(owner_resource.pk), owner_resource.name)
        expected_final_path = os.path.join(expected_owner_directory, expected_filename)

        mock_make_local_dir.assert_not_called()
        mock_move_resource.assert_called_with(owner_resource.path, expected_final_path)