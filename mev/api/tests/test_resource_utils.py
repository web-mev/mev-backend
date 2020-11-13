import os
import random
import uuid
import unittest
import unittest.mock as mock

from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from rest_framework.exceptions import ValidationError

from resource_types import RESOURCE_MAPPING, \
    DB_RESOURCE_STRING_TO_HUMAN_READABLE
from api.models import Resource, \
    Workspace, \
    ResourceMetadata, \
    ExecutedOperation, \
    Operation
from api.utilities.resource_utilities import move_resource_to_final_location, \
    get_resource_view, \
    validate_resource, \
    handle_valid_resource, \
    handle_invalid_resource, \
    check_extension, \
    check_for_resource_operations
from api.utilities.operations import read_operation_json
from api.tests.base import BaseAPITestCase
from api.tests import test_settings

TESTDIR = os.path.dirname(__file__)
TESTDIR = os.path.join(TESTDIR, 'operation_test_files')

class TestResourceUtilities(BaseAPITestCase):
    '''
    Tests the functions contained in the api.utilities.resource_utilities
    module.
    '''
    def setUp(self):
        self.establish_clients()
        

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
    def test_proper_invalid_handler_called(self, mock_get_storage_backend, mock_handle_valid_resource, mock_get_resource_type_instance):
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

    @mock.patch('api.utilities.resource_utilities.get_operation_instance_data')
    def test_check_for_resource_operations_case1(self, mock_get_operation_instance_data):
        '''
        When removing a Resource from a Workspace, we need to ensure
        we are not removing a file that has been used in one or more 
        ExecutedOperations.

        Below, we check where a file HAS been used and show that the 
        function returns True
        '''
        # need to create an ExecutedOperation that is based on a known
        # Operation and part of an existing workspace. Also need to ensure
        # that there is a Resource that is being used in that Workspace

        all_workspaces = Workspace.objects.all()
        workspace_with_resource = None
        for w in all_workspaces:
            if len(w.resources.all()) > 0:
                workspace_with_resource = w
        if workspace_with_resource is None:
            raise ImproperlyConfigured('Need at least one Workspace that has'
                 ' at least a single Resource.'
            )

        ops = Operation.objects.all()
        if len(ops) > 0:
            op = ops[0]
        else:
            raise ImproperlyConfigured('Need at least one Operation'
                ' to use for this test'
            )
        
        f = os.path.join(
            TESTDIR,
            'valid_operation.json'
        )
        op_data = read_operation_json(f)
        mock_get_operation_instance_data.return_value = op_data
        executed_op_pk = uuid.uuid4()
        # the op_data we get from above has two outputs, one of which
        # is a DataResource. Just to be sure everything is consistent
        # between the spec and our mocked inputs below, we do this assert:
        input_keyset = list(op_data['inputs'].keys())
        self.assertCountEqual(input_keyset, ['count_matrix','p_val'])

        mock_used_resource = workspace_with_resource.resources.all()[0]
        mock_validated_inputs = {
            'count_matrix': str(mock_used_resource.pk), 
            'p_val': 0.01
        }
        ex_op = ExecutedOperation.objects.create(
            id=executed_op_pk,
            workspace=workspace_with_resource,
            job_name = 'abc',
            inputs = mock_validated_inputs,
            outputs = {},
            operation = op,
            mode = op_data['mode'],
            status = ExecutedOperation.SUBMITTED
        )
        was_used = check_for_resource_operations(mock_used_resource, workspace_with_resource)
        self.assertTrue(was_used)


    @mock.patch('api.utilities.resource_utilities.get_operation_instance_data')
    def test_check_for_resource_operations_case2(self, mock_get_operation_instance_data):
        '''
        When removing a Resource from a Workspace, we need to ensure
        we are not removing a file that has been used in one or more 
        ExecutedOperations.

        Below, we check where a file HAS NOT been used and show that the 
        function returns False
        '''
        # need to create an ExecutedOperation that is based on a known
        # Operation and part of an existing workspace. Also need to ensure
        # that there is a Resource that is being used in that Workspace

        all_workspaces = Workspace.objects.all()
        workspace_with_resource = None
        for w in all_workspaces:
            if len(w.resources.all()) > 0:
                workspace_with_resource = w
        if workspace_with_resource is None:
            raise ImproperlyConfigured('Need at least one Workspace that has'
                 ' at least a single Resource.'
            )

        ops = Operation.objects.all()
        if len(ops) > 0:
            op = ops[0]
        else:
            raise ImproperlyConfigured('Need at least one Operation'
                ' to use for this test'
            )
        
        f = os.path.join(
            TESTDIR,
            'simple_op_test.json'
        )
        op_data = read_operation_json(f)
        mock_get_operation_instance_data.return_value = op_data
        executed_op_pk = uuid.uuid4()
        # the op_data we get from above has two outputs, one of which
        # is a DataResource. Just to be sure everything is consistent
        # between the spec and our mocked inputs below, we do this assert:
        input_keyset = list(op_data['inputs'].keys())
        self.assertCountEqual(input_keyset, ['some_string'])

        mock_used_resource = workspace_with_resource.resources.all()[0]
        mock_validated_inputs = {
            'some_string': 'xyz'
        }
        ex_op = ExecutedOperation.objects.create(
            id=executed_op_pk,
            workspace=workspace_with_resource,
            job_name = 'abc',
            inputs = mock_validated_inputs,
            outputs = {},
            operation = op,
            mode = op_data['mode'],
            status = ExecutedOperation.SUBMITTED
        )
        was_used = check_for_resource_operations(mock_used_resource, workspace_with_resource)
        self.assertFalse(was_used)

    # def test_all_resources_have_acceptable_extensions(self):
    #     '''
    #     This tests that all the known Resource types have the required
    #     ACCEPTABLE_EXTENSIONS key. Could more appropriately be placed
    #     inside the resource_types folder, but that would require 
    #     '''
    #     pass


