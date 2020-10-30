import os
import random
import unittest
import unittest.mock as mock

from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from rest_framework.exceptions import ValidationError

from resource_types import RESOURCE_MAPPING, \
    DB_RESOURCE_STRING_TO_HUMAN_READABLE
from api.models import Resource, Workspace, ResourceMetadata
from api.utilities.resource_utilities import move_resource_to_final_location, \
    copy_resource_to_workspace, \
    check_for_shared_resource_file, \
    get_resource_view, \
    validate_resource, \
    handle_valid_resource, \
    handle_invalid_resource, \
    check_extension
from api.tests.base import BaseAPITestCase
from api.tests import test_settings

class TestResourceUtilities(BaseAPITestCase):
    '''
    Tests the functions contained in the api.utilities.resource_utilities
    module.
    '''
    def setUp(self):
        self.establish_clients()


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

    @mock.patch('resource_types.RESOURCE_MAPPING')
    @mock.patch('api.utilities.resource_utilities.get_storage_backend')
    def test_resource_preview_for_valid_resource_type(self, mock_get_storage_backend, mock_resource_mapping):
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
            def get_contents(self, path, query_params={}):
                return expected_dict

        mock_resource_mapping.__getitem__.return_value = mock_resource_type_class
        mock_storage_backend = mock.MagicMock()
        mock_storage_backend.get_local_resource_path.return_value = '/foo'
        mock_get_storage_backend.return_value = mock_storage_backend
        preview_dict = get_resource_view(r)
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

        preview_dict = get_resource_view(r)
        self.assertIsNone(preview_dict)
        

    @mock.patch('api.utilities.resource_utilities.get_resource_type_instance')
    @mock.patch('api.utilities.resource_utilities.handle_invalid_resource')
    @mock.patch('api.utilities.resource_utilities.get_storage_backend')
    def test_invalid_handler_called(self, mock_get_storage_backend, \
            mock_handle_invalid_resource, mock_get_resource_type_instance):
        '''
        Here we test that a failure to validate the resource calls the proper
        handler function.
        '''
        all_resources = Resource.objects.all()
        unset_resources = []
        for r in all_resources:
            if not r.resource_type:
                unset_resources.append(r)
        
        if len(unset_resources) == 0:
            raise ImproperlyConfigured('Need at least one'
                ' Resource without a type to test properly.'
            )

        unset_resource = unset_resources[0]

        mock_resource_class_instance = mock.MagicMock()
        mock_resource_class_instance.validate_type.return_value = (False, 'some string')
        mock_get_resource_type_instance.return_value = mock_resource_class_instance
        
        mock_storage_backend = mock.MagicMock()
        mock_storage_backend.get_local_resource_path.return_value = 'foo'
        mock_get_storage_backend.return_value = mock_storage_backend

        validate_resource(unset_resource, 'MTX')

        mock_handle_invalid_resource.assert_called()


    @mock.patch('api.utilities.resource_utilities.get_resource_type_instance')
    @mock.patch('api.utilities.resource_utilities.handle_valid_resource')
    @mock.patch('api.utilities.resource_utilities.get_storage_backend')
    def test_valid_invalid_handler_called(self, mock_get_storage_backend, mock_handle_valid_resource, mock_get_resource_type_instance):
        '''
        Here we test that a successful validation calls the proper
        handler function.
        '''
        all_resources = Resource.objects.all()
        unset_resources = []
        for r in all_resources:
            if not r.resource_type:
                unset_resources.append(r)
        
        if len(unset_resources) == 0:
            raise ImproperlyConfigured('Need at least one'
                ' Resource without a type to test properly.'
            )

        unset_resource = unset_resources[0]

        mock_resource_class_instance = mock.MagicMock()
        mock_resource_class_instance.validate_type.return_value = (True, 'some string')
        mock_get_resource_type_instance.return_value = mock_resource_class_instance

        validate_resource(unset_resource, 'MTX')

        mock_handle_valid_resource.assert_called()

    def test_unset_resource_type_does_not_change_if_validation_fails(self):
        '''
        If we had previously validated a resource successfully, requesting
        a change that fails validation results in NO change to the resource_type
        attribute
        '''
        all_resources = Resource.objects.all()
        unset_resources = []
        for r in all_resources:
            if not r.resource_type:
                unset_resources.append(r)
        
        if len(unset_resources) == 0:
            raise ImproperlyConfigured('Need at least one'
                ' Resource without a type to test properly.'
            )

        unset_resource = unset_resources[0]

        handle_invalid_resource(unset_resource, 'MTX')
        self.assertIsNone(unset_resource.resource_type)

    def test_resource_type_does_not_change_if_validation_fails(self):
        '''
        If we had previously validated a resource successfully, requesting
        a change that fails validation results in NO change to the resource_type
        attribute
        '''
        all_resources = Resource.objects.all()
        set_resources = []
        for r in all_resources:
            if r.resource_type:
                set_resources.append(r)
        
        if len(set_resources) == 0:
            raise ImproperlyConfigured('Need at least one'
                ' Resource with a type to test properly.'
            )

        resource = set_resources[0]
        original_type = resource.resource_type
        other_type = original_type
        while other_type == original_type:
            other_type = random.choice(list(RESOURCE_MAPPING.keys()))
        handle_invalid_resource(resource, other_type)

        self.assertTrue(resource.resource_type == original_type)
        self.assertTrue(resource.status == Resource.REVERTED.format(
            requested_resource_type=DB_RESOURCE_STRING_TO_HUMAN_READABLE[other_type],
            original_resource_type = DB_RESOURCE_STRING_TO_HUMAN_READABLE[original_type]
        ))

    @mock.patch.dict('api.utilities.resource_utilities.DB_RESOURCE_STRING_TO_HUMAN_READABLE', \
        {'foo_type': 'Table'})
    @mock.patch('api.utilities.resource_utilities.extension_is_consistent_with_type')
    @mock.patch('api.utilities.resource_utilities.get_acceptable_extensions')
    def test_inconsistent_file_extension_sets_status(self,
        mock_get_acceptable_extensions,
        mock_extension_is_consistent_with_type):
        '''
        This tests the case where a user selects a resource type but the
        file does not have a name that is consistent with that type. We need
        to enforce consistent extensions so we know how to try parsing files.
        For instance, a name like "file.txt" does not help us, and we do not want
        to try all different parsers.
        '''
        mock_extension_is_consistent_with_type.return_value = False
        mock_get_acceptable_extensions.return_value = ['tsv', 'csv', 'abc']
        requested_type = 'foo_type'
        human_readable_type = 'Table'
        resource = Resource.objects.all()[0]
        check_extension(resource, requested_type)
        expected_status = Resource.UNKNOWN_EXTENSION_ERROR.format(
            readable_resource_type = human_readable_type,
            filename = resource.name,
            extensions_csv = 'tsv,csv,abc'
        )
        self.assertEqual(resource.status, expected_status)

    # def test_all_resources_have_acceptable_extensions(self):
    #     '''
    #     This tests that all the known Resource types have the required
    #     ACCEPTABLE_EXTENSIONS key. Could more appropriately be placed
    #     inside the resource_types folder, but that would require 
    #     '''
    #     pass


