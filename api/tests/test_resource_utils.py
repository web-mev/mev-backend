import os
import unittest
import unittest.mock as mock

from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from rest_framework.exceptions import ValidationError

from api.models import Resource, Workspace
from api.utilities.resource_utilities import create_resource_from_upload, \
    move_resource_to_final_location, \
    copy_resource_to_workspace
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

    @mock.patch('api.utilities.resource_utilities.os.path.exists')
    @mock.patch('api.utilities.resource_utilities.move_resource')
    @mock.patch('api.utilities.resource_utilities.copy_local_resource')
    def test_copy_to_workspace(self, mock_local_copy, mock_move, mock_os_exists):
        '''
        Tests that "attaching" a resource to a workspace creates the necesary copy
        of the file (assert is called, at least) and that the database object
        is created appropriately.
        '''
        # setup the mock:
        tmp_path = '/tmp/something.tsv'
        final_path = '/some/final/path/abc.tsv'
        mock_local_copy.return_value = tmp_path
        mock_os_exists.return_value = True # mocking that the user storage dir exists
        mock_move.return_value = final_path 

        unattached_resources = Resource.objects.filter(workspace=None, is_public=True)
        if len(unattached_resources) == 0:
            raise ImproperlyConfigured('Need at least one unattached Resource'
                ' to test the workspace-add function.')
        
        r = unattached_resources[0]

        # extract the attributes of the resource so we can check 
        # for any changes later
        orig_path = r.path
        orig_pk = r.pk

        owner = r.owner
        owner_workspaces = Workspace.objects.filter(owner=owner)
        if len(owner_workspaces) == 0:
            raise ImproperlyConfigured('Need at least one Workspace'
                ' to attach to (for this owner)')

        workspace = owner_workspaces[0]

        # now have a workspace and owner.  Check initial state:
        workspace_resources = Resource.objects.filter(workspace=workspace)
        n0 = len(workspace_resources)

        # call the method
        new_resource = copy_resource_to_workspace(r, workspace)

        # check that the proper functions were called:
        mock_local_copy.assert_called()
        mock_move.assert_called()

        # check that there is a new resource and it is associated
        # with the workspace
        workspace_resources = Resource.objects.filter(workspace=workspace)
        n1 = len(workspace_resources)
        self.assertEqual(n1-n0, 1)

        # check the contents of the returned "new" Resource
        self.assertEqual(new_resource.path, final_path)
        self.assertEqual(new_resource.workspace, workspace)
        self.assertFalse(new_resource.pk == orig_pk)
        # check that the new resource is private
        self.assertFalse(new_resource.is_public)

        # check that the original resource did not change
        orig_resource = Resource.objects.get(pk=orig_pk)
        self.assertEqual(orig_resource.path, orig_path)
        self.assertIsNone(orig_resource.workspace)
        self.assertTrue(orig_resource.is_public)

   
