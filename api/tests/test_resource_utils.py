import os
import unittest
import unittest.mock as mock

from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from rest_framework.exceptions import ValidationError

from api.models import Resource, Workspace, ResourceMetadata
from api.utilities.resource_utilities import create_resource_from_upload, \
    move_resource_to_final_location, \
    copy_resource_to_workspace, \
    check_for_shared_resource_file, \
    get_resource_preview
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

    def test_copy_to_workspace(self):
        '''
        Tests that "attaching" a resource to a workspace creates the
        appropriate database objects.
        '''

        unattached_resources = Resource.objects.filter(
            workspace=None, 
            is_active = True,
            is_public=True).exclude(resource_type__isnull=True)
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
        resource_metadata = ResourceMetadata.objects.all()
        rm_n0 = len(resource_metadata)

        # call the method
        new_resource = copy_resource_to_workspace(r, workspace)

        # check that there is a new resource and it is associated
        # with the workspace
        workspace_resources = Resource.objects.filter(workspace=workspace)
        n1 = len(workspace_resources)
        self.assertEqual(n1-n0, 1)

        # check that there is new ResourceMetadata added:
        resource_metadata = ResourceMetadata.objects.all()
        rm_n1 = len(resource_metadata)
        self.assertEqual(rm_n1-rm_n0, 1)

        # check that there is metadata associated with the new Resource
        new_resource_metadata = ResourceMetadata.objects.filter(resource=new_resource)
        self.assertEqual(len(new_resource_metadata), 1)

        # double-check that the original resource still has its ResourceMetadata
        orig_resource_metadata = ResourceMetadata.objects.filter(resource=r)
        self.assertEqual(len(orig_resource_metadata), 1)

        # check the contents of the returned "new" Resource
        self.assertEqual(new_resource.path, orig_path)
        self.assertEqual(new_resource.workspace, workspace)
        self.assertFalse(new_resource.pk == orig_pk)
        # check that the new resource is private
        self.assertFalse(new_resource.is_public)

        # check that the original resource did not change
        orig_resource = Resource.objects.get(pk=orig_pk)
        self.assertEqual(orig_resource.path, orig_path)
        self.assertIsNone(orig_resource.workspace)
        self.assertTrue(orig_resource.is_public)


    def test_for_multiple_resources_referencing_single_file_case1(self):
        '''
        This tests the function which checks to see if a single file
        is referenced by multiple Resource instances, as would be the case once 
        Resources are added to Workspaces.
        '''
        all_resources = Resource.objects.all()
        d = {}
        repeated_resources = []
        for r in all_resources:
            if r.path in d:
                repeated_resources.append(r)
            else:
                d[r.path] = 1
            
        if len(repeated_resources) == 0:
            raise ImproperlyConfigured('Need at least two Resources that have'
            ' the same path to run this test.')

        # just get the first Resource to use for the test
        r = repeated_resources[0]
        self.assertTrue(check_for_shared_resource_file(r))

    def test_for_multiple_resources_referencing_single_file_case2(self):
        '''
        This tests the function which checks to see if a single file
        is referenced by multiple Resource instances, as would be the case once 
        Resources are added to Workspaces.

        Here, we check that 1:1 correspondance returns False
        '''
        r = Resource.objects.filter(path='/path/to/fileB.txt')
        if len(r) != 1:
            raise ImproperlyConfigured('Need a Resource with a unique'
                ' path to run this test.')

        self.assertFalse(check_for_shared_resource_file(r[0]))        

    @mock.patch('api.utilities.resource_utilities.RESOURCE_MAPPING')
    def test_resource_preview_for_valid_resource_type(self, mock_resource_mapping):
        '''
        Tests that a proper preview dict is returned.  Mocks out the 
        method that does the reading of the resource path.
        '''
        all_resources = Resource.objects.all()
        resource = None
        for r in all_resources:
            if r.resource_type:
                resource = r
                break
        if not resource:
            raise ImproperlyConfigured('Need at least one resource with'
                ' a specified resource_type to run this test.'
            )

        expected_dict = {'a': 1, 'b':2}

        class mock_resource_type_class(object):
            def get_preview(self, path):
                return expected_dict

        mock_resource_mapping.__getitem__.return_value = mock_resource_type_class

        preview_dict = get_resource_preview(r)
        self.assertDictEqual(expected_dict, preview_dict)


    def test_resource_preview_for_null_resource_type(self):
        '''
        Tests that a proper preview dict is returned.  Mocks out the 
        method that does the reading of the resource path.
        '''
        all_resources = Resource.objects.all()
        resource = None
        for r in all_resources:
            if r.resource_type is None:
                resource = r
                break
        if not resource:
            raise ImproperlyConfigured('Need at least one resource without'
                ' a specified resource_type to run this test.'
            )

        preview_dict = get_resource_preview(r)
        self.assertTrue('info' in preview_dict)
        

    @mock.patch('api.utilities.resource_utilities.RESOURCE_MAPPING')
    def test_resource_preview_for_invalid_resource_type(self, mock_resource_mapping):
        '''
        Tests that a proper preview dict is returned.  Mocks out the 
        method that does the reading of the resource path.
        '''
        all_resources = Resource.objects.all()
        resource = None
        for r in all_resources:
            if r.resource_type:
                resource = r
                break
        if not resource:
            raise ImproperlyConfigured('Need at least one resource with'
                ' a specified resource_type to run this test.'
            )

        mock_resource_mapping.__getitem__.side_effect = KeyError

        preview_dict = get_resource_preview(r)
        self.assertTrue('error' in preview_dict)
