import os
import copy
import random
import uuid
import unittest
import unittest.mock as mock

from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from rest_framework.exceptions import ValidationError

from constants import DB_RESOURCE_KEY_TO_HUMAN_READABLE, \
    OBSERVATION_SET_KEY, \
    FEATURE_SET_KEY, \
    PARENT_OP_KEY, \
    RESOURCE_KEY, \
    TSV_FORMAT, \
    WILDCARD
from resource_types import RESOURCE_MAPPING, \
    GeneralResource, \
    AnnotationTable, \
    Matrix, \
    DataResource
from api.models import Resource, \
    Workspace, \
    ResourceMetadata, \
    ExecutedOperation, \
    WorkspaceExecutedOperation, \
    Operation, \
    OperationResource
from api.serializers.resource_metadata import ResourceMetadataSerializer
from api.utilities.resource_utilities import move_resource_to_final_location, \
    get_resource_view, \
    validate_resource, \
    handle_valid_resource, \
    handle_invalid_resource, \
    check_file_format_against_type, \
    add_metadata_to_resource, \
    get_resource_by_pk, \
    write_resource, \
    retrieve_resource_class_instance
from api.utilities.operations import read_operation_json, \
    check_for_resource_operations
from api.exceptions import NoResourceFoundException, \
    ResourceValidationException
from api.tests.base import BaseAPITestCase
from api.tests import test_settings

BASE_TESTDIR = os.path.dirname(__file__)
TESTDIR = os.path.join(BASE_TESTDIR, 'operation_test_files')
VAL_TESTDIR = os.path.join(BASE_TESTDIR, 'resource_validation_test_files')

class TestResourceUtilities(BaseAPITestCase):
    '''
    Tests the functions contained in the api.utilities.resource_utilities
    module.
    '''
    def setUp(self):
        self.establish_clients()
        

    def test_get_resource_by_pk_works_for_all_resources(self):
        '''
        We use the api.utilities.resource_utilities.get_resource_by_pk
        function to check for the existence of all children of the 
        AbstractResource class. Test that it all works as expected.
        '''
        with self.assertRaises(NoResourceFoundException):
            get_resource_by_pk(uuid.uuid4())

        r = Resource.objects.all()
        r = r[0]
        r2 = get_resource_by_pk(r.pk)
        self.assertEqual(r,r2)

        ops = Operation.objects.all()
        op = ops[0]
        r3 = OperationResource.objects.create(
            operation = op,
            input_field = 'foo',
            name = 'foo.txt',
            resource_type = 'MTX'
        )
        r4 = get_resource_by_pk(r3.pk)
        self.assertEqual(r3,r4)

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
            def get_contents(self, path, file_extension, query_params={}):
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
        
    @mock.patch('api.utilities.resource_utilities.get_contents')
    @mock.patch('api.utilities.resource_utilities.get_storage_backend')
    def test_resource_preview_for_general_type_does_not_pull_file(self, 
        mock_get_storage_backend,
        mock_get_contents):
        '''
        If the resource type is such that we cannot generate a preview (e.g.
        for a general file type), then check that we don't bother to pull
        the resource to the local cache
        '''
        all_resources = Resource.objects.all()
        resource = all_resources[0]
        resource.resource_type = WILDCARD

        mock_storage_backend = mock.MagicMock()
        mock_get_storage_backend.return_value = mock_storage_backend

        preview_dict = get_resource_view(resource)
        self.assertIsNone(preview_dict)
        mock_storage_backend.get_local_resource_path.assert_not_called()
        mock_get_contents.assert_not_called()

    @mock.patch('api.utilities.resource_utilities.get_resource_type_instance')
    @mock.patch('api.utilities.resource_utilities.handle_invalid_resource')
    @mock.patch('api.utilities.resource_utilities.get_storage_backend')
    @mock.patch('api.utilities.resource_utilities.check_file_format_against_type')
    def test_invalid_handler_called(self, mock_check_file_format_against_type, \
            mock_get_storage_backend, \
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

        validate_resource(unset_resource, 'MTX', 'csv')

        mock_handle_invalid_resource.assert_called()


    @mock.patch('api.utilities.resource_utilities.get_resource_type_instance')
    @mock.patch('api.utilities.resource_utilities.handle_valid_resource')
    @mock.patch('api.utilities.resource_utilities.get_storage_backend')
    @mock.patch('api.utilities.resource_utilities.check_file_format_against_type')
    def test_proper_valid_handler_called(self, \
        mock_check_file_format_against_type, \
        mock_get_storage_backend, \
        mock_handle_valid_resource, \
        mock_get_resource_type_instance):
        '''
        Here we test that a successful validation calls the proper
        handler function.
        '''
        mock_local_path = '/some/local/path.txt'
        mock_storage_backend = mock.MagicMock()
        mock_storage_backend.get_local_resource_path.return_value = mock_local_path
        mock_get_storage_backend.return_value = mock_storage_backend

        mock_resource_class_instance = mock.MagicMock()
        mock_resource_class_instance.performs_validation.return_value = True
        mock_resource_class_instance.validate_type.return_value = (True, 'some string')
        mock_get_resource_type_instance.return_value = mock_resource_class_instance

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


        validate_resource(unset_resource, 'MTX', TSV_FORMAT)

        mock_handle_valid_resource.assert_called()

    @mock.patch('api.utilities.resource_utilities.get_resource_type_instance')
    @mock.patch('api.utilities.resource_utilities.handle_valid_resource')
    @mock.patch('api.utilities.resource_utilities.get_storage_backend')
    @mock.patch('api.utilities.resource_utilities.check_file_format_against_type')
    def test_proper_exceptions_raised_case1(self, \
        mock_check_file_format_against_type, \
        mock_get_storage_backend, \
        mock_handle_valid_resource, \
        mock_get_resource_type_instance):
        '''
        If unexpected errors (like connecting to cloud storage occur), check that we raise exceptions
        that provide helpful errors.

        Here, we test if the `check_file_format_against_type` function raises an exception. Note that
        a predictable failure there (i.e. an inconsistent resource type and format were specified), then
        the function raises a ResourceValidationException. Since this exception is not expected, it is NOT
        of that type.
        '''
        mock_check_file_format_against_type.side_effect = [Exception('something unexpected!')]

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

        with self.assertRaisesRegex(Exception, 'something unexpected'):
            validate_resource(unset_resource, 'MTX', TSV_FORMAT)
        mock_handle_valid_resource.assert_not_called()
        mock_get_storage_backend.assert_not_called()
        mock_get_resource_type_instance.assert_not_called()

    @mock.patch('api.utilities.resource_utilities.get_resource_type_instance')
    @mock.patch('api.utilities.resource_utilities.handle_valid_resource')
    @mock.patch('api.utilities.resource_utilities.get_storage_backend')
    @mock.patch('api.utilities.resource_utilities.check_file_format_against_type')
    def test_proper_exceptions_raised_case2(self, \
        mock_check_file_format_against_type, \
        mock_get_storage_backend, \
        mock_handle_valid_resource, \
        mock_get_resource_type_instance):
        '''
        If unexpected errors (like connecting to cloud storage occur), check that we raise exceptions
        that provide helpful errors.

        Here, we test if the `get_resource_type` function raises an exception from something
        unexpected
        '''
        mock_get_resource_type_instance.side_effect = [Exception('ack'),]

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

        with self.assertRaisesRegex(Exception, 'ack'):
            validate_resource(unset_resource, 'MTX', TSV_FORMAT)
        mock_handle_valid_resource.assert_not_called()
        mock_get_storage_backend.assert_not_called()
        mock_get_resource_type_instance.assert_called()

    @mock.patch('api.utilities.resource_utilities.get_resource_type_instance')
    @mock.patch('api.utilities.resource_utilities.handle_valid_resource')
    @mock.patch('api.utilities.resource_utilities.get_storage_backend')
    @mock.patch('api.utilities.resource_utilities.check_file_format_against_type')
    def test_proper_exceptions_raised_case3(self, \
        mock_check_file_format_against_type, \
        mock_get_storage_backend, \
        mock_handle_valid_resource, \
        mock_get_resource_type_instance):
        '''
        If unexpected errors (like connecting to cloud storage occur), check that we raise exceptions
        that provide helpful errors.

        Here, we test if the `get_resource_type` function raises an exception from an unknown
        resource type (a keyError). 
        '''
        mock_get_resource_type_instance.side_effect = [KeyError('abc'),]

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

        with self.assertRaisesRegex(Exception, 'ZZZ'):
            validate_resource(unset_resource, 'ZZZ', TSV_FORMAT)
        mock_handle_valid_resource.assert_not_called()
        mock_get_storage_backend.assert_not_called()
        mock_get_resource_type_instance.assert_called()

    @mock.patch('api.utilities.resource_utilities.get_resource_type_instance')
    @mock.patch('api.utilities.resource_utilities.handle_valid_resource')
    @mock.patch('api.utilities.resource_utilities.get_storage_backend')
    @mock.patch('api.utilities.resource_utilities.check_file_format_against_type')
    def test_proper_exceptions_raised_case4(self, \
        mock_check_file_format_against_type, \
        mock_get_storage_backend, \
        mock_handle_valid_resource, \
        mock_get_resource_type_instance):
        '''
        If unexpected errors (like connecting to cloud storage occur), check that we raise exceptions
        that provide helpful errors.

        Here, we test if the get_local_resource_path (a method of the storage backend) fails
        for some unexpected reason, such as failure to connect to cloud storage
        '''

        # here we mock there being a problem with the storage backend (maybe bucket storage
        # service is temporarily offline?)
        mock_storage_backend = mock.MagicMock()
        mock_storage_backend.get_local_resource_path.side_effect = [Exception('something bad')]
        mock_get_storage_backend.return_value = mock_storage_backend

        mock_resource_class_instance = mock.MagicMock()
        mock_resource_class_instance.performs_validation.return_value = True
        mock_get_resource_type_instance.return_value = mock_resource_class_instance

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

        expected_message_partial = ('An unexpected issue occurred when'
            ' moving the file for inspection')
        with self.assertRaisesRegex(Exception, expected_message_partial):
            validate_resource(unset_resource, 'MTX', TSV_FORMAT)
    
        mock_resource_class_instance.validate_type.assert_not_called()
        mock_handle_valid_resource.assert_not_called()

    @mock.patch('api.utilities.resource_utilities.get_resource_type_instance')
    @mock.patch('api.utilities.resource_utilities.handle_valid_resource')
    @mock.patch('api.utilities.resource_utilities.get_storage_backend')
    @mock.patch('api.utilities.resource_utilities.check_file_format_against_type')
    def test_proper_exceptions_raised_case5(self, \
        mock_check_file_format_against_type, \
        mock_get_storage_backend, \
        mock_handle_valid_resource, \
        mock_get_resource_type_instance):
        '''
        If unexpected errors (like connecting to cloud storage occur), check that we raise exceptions
        that provide helpful errors.

        Here, we test if the validation method fails unexpectedly.
        '''
        mock_local_path = '/some/local/path.txt'
        mock_storage_backend = mock.MagicMock()
        mock_storage_backend.get_local_resource_path.return_value = mock_local_path
        mock_get_storage_backend.return_value = mock_storage_backend
        mock_resource_class_instance = mock.MagicMock()
        mock_resource_class_instance.performs_validation.return_value = True
        mock_resource_class_instance.validate_type.side_effect = [Exception('something unexpected.')]
        mock_get_resource_type_instance.return_value = mock_resource_class_instance

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

        with self.assertRaisesRegex(Exception, Resource.UNEXPECTED_VALIDATION_ERROR):
            validate_resource(unset_resource, 'MTX', TSV_FORMAT)

        mock_handle_valid_resource.assert_not_called()

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
        with self.assertRaises(ResourceMetadata.DoesNotExist):
            metadata = ResourceMetadata.objects.get(resource=unset_resource)

        handle_invalid_resource(unset_resource, 'MTX')
        self.assertIsNone(unset_resource.resource_type)
        # now the metadata query should succeed
        metadata = ResourceMetadata.objects.get(resource=unset_resource)
        self.assertTrue(metadata)

    @mock.patch('api.utilities.resource_utilities.add_metadata_to_resource')
    def test_resource_type_does_not_change_if_validation_fails(self, \
        mock_add_metadata_to_resource
    ):
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
        self.assertTrue(resource.status.startswith(Resource.REVERTED.format(
            requested_resource_type=DB_RESOURCE_KEY_TO_HUMAN_READABLE[other_type],
            original_resource_type = DB_RESOURCE_KEY_TO_HUMAN_READABLE[original_type])
        ))
        mock_add_metadata_to_resource.assert_not_called()

    @mock.patch.dict('api.utilities.resource_utilities.DB_RESOURCE_KEY_TO_HUMAN_READABLE', \
        {'foo_type': 'Table'})
    @mock.patch('api.utilities.resource_utilities.format_is_acceptable_for_type')
    @mock.patch('api.utilities.resource_utilities.get_acceptable_formats')
    def test_inconsistent_file_extension_raises_proper_ex(self,
        mock_get_acceptable_formats,
        mock_format_is_acceptable_for_type):
        '''
        This tests the case where a user selects a resource type but the
        file does not have a format that is consistent with that type. We need
        to enforce canonical formats so we know how to try parsing files.
        '''
        mock_format_is_acceptable_for_type.return_value = False
        mock_get_acceptable_formats.return_value = ['tsv', 'csv', 'abc']
        requested_type = 'foo_type'
        human_readable_type = 'Table'
        file_format = 'xyz'
        with self.assertRaises(ResourceValidationException) as ex:
            check_file_format_against_type(requested_type, file_format)
            expected_status = Resource.UNKNOWN_FORMAT_ERROR.format(
                readable_resource_type = human_readable_type,
                fmt = resource.file_format,
                extensions_csv = 'tsv,csv,abc'
            )
            self.assertEqual(str(ex), expected_status)

    @mock.patch('api.utilities.resource_utilities.format_is_acceptable_for_type')
    def test_bad_resource_type_when_checking_type_and_format(self,
        mock_format_is_acceptable_for_type):
        '''
        This tests the case where a user selects a resource type that does not
        exist and the underlying function raises an exception
        '''
        mock_format_is_acceptable_for_type.side_effect = KeyError('ack')
        requested_type = 'foo_type'
        file_format = 'xyz'
        with self.assertRaises(ResourceValidationException) as ex:
            check_file_format_against_type(requested_type, file_format)
            expected_status = Resource.UNKNOWN_RESOURCE_TYPE_ERROR.format(
                requested_resource_type = requested_type
            )
            self.assertEqual(str(ex), expected_status)

    @mock.patch('api.utilities.resource_utilities.get_resource_type_instance')
    def test_bad_resource_type_when_retrieving_resource_type_instance(self,
        mock_get_resource_type_instance):
        '''
        This tests the case where a user selects a resource type that does not
        exist and the underlying function raises a KeyError
        '''
        mock_get_resource_type_instance.side_effect = KeyError('ack')
        requested_type = 'foo_type'
        with self.assertRaises(ResourceValidationException) as ex:
            retrieve_resource_class_instance(requested_type)
            expected_status = Resource.UNKNOWN_RESOURCE_TYPE_ERROR.format(
                requested_resource_type = requested_type
            )
            self.assertEqual(str(ex), expected_status)

    @mock.patch('api.utilities.resource_utilities.get_resource_type_instance')
    def test_unexpected_exception_when_retrieving_resource_type_instance(self,
        mock_get_resource_type_instance):
        '''
        This tests the case where a user selects a resource type that does not
        exist and the underlying function raises an exception
        '''
        mock_get_resource_type_instance.side_effect = Exception('ack')
        with self.assertRaises(Exception) as ex:
            retrieve_resource_class_instance(requested_type)

    @mock.patch('api.utilities.operations.get_operation_instance_data')
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
            'valid_workspace_operation.json'
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
        ex_op = WorkspaceExecutedOperation.objects.create(
            id=executed_op_pk,
            owner = self.regular_user_1, 
            workspace = workspace_with_resource,
            job_name = 'abc',
            inputs = mock_validated_inputs,
            outputs = {},
            operation = op,
            mode = op_data['mode'],
            status = ExecutedOperation.SUBMITTED
        )
        was_used = check_for_resource_operations(mock_used_resource, workspace_with_resource)
        self.assertTrue(was_used)


    @mock.patch('api.utilities.operations.get_operation_instance_data')
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
            'simple_workspace_op_test.json'
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
        ex_op = WorkspaceExecutedOperation.objects.create(
            id=executed_op_pk,
            owner = self.regular_user_1,
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

    @mock.patch('api.utilities.operations.get_operation_instance_data')
    def test_check_for_resource_operations_case3(self, mock_get_operation_instance_data):
        '''
        When removing a Resource from a Workspace, we need to ensure
        we are not removing a file that has been used in one or more 
        ExecutedOperations.

        Below, we check where a file HAS been used, but the analysis
        failed. Hence, it's safe to remove since it was not used to
        create anything.
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
            'valid_workspace_operation.json'
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
        ex_op = WorkspaceExecutedOperation.objects.create(
            id=executed_op_pk,
            owner = self.regular_user_1, 
            workspace = workspace_with_resource,
            job_name = 'abc',
            inputs = mock_validated_inputs,
            outputs = {},
            operation = op,
            mode = op_data['mode'],
            status = ExecutedOperation.COMPLETION_ERROR,
            job_failed = True
        )
        was_used = check_for_resource_operations(mock_used_resource, workspace_with_resource)
        self.assertFalse(was_used)


    @mock.patch('api.utilities.resource_utilities.get_resource_type_instance')
    @mock.patch('api.utilities.resource_utilities.handle_valid_resource')
    @mock.patch('api.utilities.resource_utilities.get_storage_backend')
    @mock.patch('api.utilities.resource_utilities.check_file_format_against_type')
    def test_proper_steps_taken_with_wildcard_resource(self, mock_check_file_format_against_type, \
        mock_get_storage_backend, \
        mock_handle_valid_resource, \
        mock_get_resource_type_instance):
        '''
        Here we test that a esource type with a "wildcard" type goes through the proper
        steps. That is, we should skip the validation, etc.
        '''
        all_resources = Resource.objects.all()
        r = all_resources[0]

        g = GeneralResource()
        mock_get_resource_type_instance.return_value = g

        validate_resource(r, WILDCARD, '')

        mock_handle_valid_resource.assert_called()
        mock_get_storage_backend.assert_not_called()

    def test_check_file_format_against_type_for_wildcard_resource(self):
        '''
        Checks that the type + format checking method just returns silently
        since we are trying to set to a wildcard/generic resource type
        '''
        self.assertIsNone(check_file_format_against_type(WILDCARD, ''))

    @mock.patch('api.utilities.resource_utilities.move_resource_to_final_location')
    def test_check_handle_valid_resource_for_wildcard_type(self, mock_move_resource_to_final_location):
        '''
        Check that we do the proper things when we handle the apparently 
        "valid" resource. For wildcard types, they are trivially valid, but
        we need to check that we are not calling any methods that wouldn't 
        make sense in this context.
        '''
        mock_move_resource_to_final_location.return_value = '/a/b/c.txt'

        all_resources = Resource.objects.all()
        r = all_resources[0]
        g = GeneralResource()
        handle_valid_resource(r, g, WILDCARD, '')

        self.assertEqual(r.path, '/a/b/c.txt')

        metadata = ResourceMetadata.objects.get(resource=r)
        self.assertIsNone(getattr(metadata, PARENT_OP_KEY))
        self.assertIsNone(getattr(metadata, FEATURE_SET_KEY))
        self.assertIsNone(getattr(metadata, OBSERVATION_SET_KEY))
        self.assertEqual(getattr(metadata, RESOURCE_KEY), r)

    @mock.patch('api.utilities.resource_utilities.move_resource_to_final_location')
    @mock.patch('api.utilities.resource_utilities.add_metadata_to_resource')
    def test_metadata_addition_failure(self, 
        mock_add_metadata_to_resource,
        mock_move_resource_to_final_location):
        '''
        Check that we do the proper things if the addition of the metadata
        to the resource fails.

        For instance, we had a case where the metadata extraction worked,
        but the sample IDs were too long. In that case, the `add_metadata_to_resource`
        function raised an uncaught exception and the Resource.path attribute
        was not set correctly.
        '''
        mock_move_resource_to_final_location.return_value = '/a/b/c.txt'
        mock_add_metadata_to_resource.side_effect = ValidationError('ack')

        all_resources = Resource.objects.all()
        r = all_resources[0]
        expected_path = r.path
        # doesn't matter what this is. However, setting the
        # performs_validation method to return False
        # avoids having to mock out a bunch of
        # other functions.
        rc = mock.MagicMock()
        rc.performs_validation.return_value = False
        rc.extract_metadata.return_value = {}
        with self.assertRaisesRegex(Exception, 'adding metadata'):
            handle_valid_resource(r, rc, WILDCARD, 'txt')

        self.assertEqual(r.path, expected_path)
        mock_move_resource_to_final_location.assert_not_called()
        self.assertIsNone(r.resource_type)

    def test_add_metadata(self):
        '''
        Test that we gracefully handle updates
        when associating metadata with a resource.

        Have a case where we update and we create a new ResourceMetadata
        '''
        # create a new Resource
        r = Resource.objects.create(
            name='foo.txt'
        )
        rm = ResourceMetadata.objects.create(
            resource=r
        )
        rm_pk = rm.pk

        mock_obs_set = {
            'multiple': True,
            'elements': [
                {
                    'id': 'sampleA'
                },
                {
                    'id': 'sampleB'
                }
            ]
        }
        add_metadata_to_resource(
            r, 
            {
                OBSERVATION_SET_KEY:mock_obs_set
            }
        )

        # query again, see that it was updated
        rm2 = ResourceMetadata.objects.get(pk=rm_pk)
        expected_obs_set = copy.deepcopy(mock_obs_set)
        elements = expected_obs_set['elements']
        for el in elements:
            el.update({'attributes': {}})
        self.assertEqual(rm2.observation_set['multiple'], mock_obs_set['multiple'])
        self.assertCountEqual(rm2.observation_set['elements'], elements)

        # OK, now get a Resource that does not already have metadata
        # associated with it:        
        r = Resource.objects.create(
            name='bar.txt'
        )
        with self.assertRaises(ResourceMetadata.DoesNotExist):
            ResourceMetadata.objects.get(resource=r)
        add_metadata_to_resource(
            r, 
            {OBSERVATION_SET_KEY:mock_obs_set}
        )

        # query again, see that it was updated
        rm3 = ResourceMetadata.objects.get(pk=rm_pk)
        expected_obs_set = copy.deepcopy(mock_obs_set)
        elements = expected_obs_set['elements']
        for el in elements:
            el.update({'attributes': {}})
        self.assertEqual(rm3.observation_set['multiple'], mock_obs_set['multiple'])
        self.assertCountEqual(rm3.observation_set['elements'], elements)
        
    @mock.patch('api.utilities.resource_utilities.ResourceMetadataSerializer')
    def test_add_metadata_case2(self, mock_serializer_cls):
        '''
        Test that we gracefully handle updates and save failures
        when associating metadata with a resource.

        Inspired by a runtime failure where the FeatureSet was too
        large for the database field
        '''
        # create a new Resource
        r = Resource.objects.create(
            name='foo.txt'
        )
        # ensure it has no associated metadata
        with self.assertRaises(ResourceMetadata.DoesNotExist):
            ResourceMetadata.objects.get(resource=r)

        # create a mock object that will raise an exception
        from django.db.utils import OperationalError
        mock_serializer1 = mock.MagicMock()
        mock_serializer2 = mock.MagicMock()
        mock_serializer1.is_valid.return_value = True
        mock_serializer1.save.side_effect = OperationalError
        mock_serializer_cls.side_effect = [mock_serializer1, mock_serializer2]
        add_metadata_to_resource(
            r, 
            {}
        )
        mock_serializer2.save.assert_called()

    @mock.patch('api.utilities.resource_utilities.make_local_directory')
    @mock.patch('api.utilities.resource_utilities.os')
    def test_resource_write_dir_fails(self, mock_os, mock_make_local_directory):
        '''
        Tests the case where we fail to create a directory
        to write into. Check that this is handled appropriately.
        '''
        mock_os.path.dirname.return_value = '/some/dir'
        mock_os.path.exists.return_value = False
        mock_make_local_directory.side_effect = Exception('something bad happened!')
        with self.assertRaises(Exception):
            write_resource('some content', '')

    @mock.patch('api.utilities.resource_utilities.make_local_directory')
    def test_resource_write_works_case1(self, mock_make_local_directory):
        '''
        Tests that we do, in fact, write correctly.
        Here, we use the /tmp folder, which exists
        '''
        self.assertTrue(os.path.exists('/tmp'))
        destination = '/tmp/some_file.txt'
        content = 'some content'
        write_resource(content, destination)
        self.assertTrue(os.path.exists(destination))
        read_content = open(destination).read()
        self.assertEqual(read_content, content)
        mock_make_local_directory.assert_not_called()
        # cleanup
        os.remove(destination)

    def test_resource_write_works_case2(self):
        '''
        Tests that we do, in fact, write correctly.
        Here, we write in a folder which doesn't already exist
        '''
        self.assertFalse(os.path.exists('/tmp/foo'))
        destination = '/tmp/foo/some_file.txt'
        content = 'some content'
        write_resource(content, destination)
        self.assertTrue(os.path.exists(destination))
        read_content = open(destination).read()
        self.assertEqual(read_content, content)
        # cleanup
        os.remove(destination)
        os.removedirs('/tmp/foo')

    def test_resource_write_only_writes_string(self):
        '''
        Tests that this function only handles strings.
        Below, we try to have it write a dict and that 
        should not work
        '''
        destination = '/tmp/some_file.txt'
        content = {'some_key': 'some_val'}
        with self.assertRaises(AssertionError):
            write_resource(content, destination)


    @mock.patch('api.utilities.resource_utilities.move_resource_to_final_location')
    @mock.patch('api.utilities.resource_utilities.get_storage_backend')
    @mock.patch('api.utilities.resource_utilities.check_file_format_against_type')
    @mock.patch('api.utilities.resource_utilities.get_resource_type_instance')
    @mock.patch('api.utilities.resource_utilities.get_local_resource_path')
    def test_metadata_when_type_changed(self, mock_get_local_resource_path, \
        mock_get_resource_type_instance, \
        mock_check_file_format_against_type, \
        mock_get_storage_backend, mock_move_resource_to_final_location):
        '''
        Checks that the update of resource metadata is updated. Related to a bug where
        a file was initially set to a general type (and thus the metadata was effectively empty).
        After trying to validate it as an annotation type, it was raising json serializer errors.
        '''
        resource_path = os.path.join(VAL_TESTDIR, 'test_annotation_valid.tsv')

        # define this mock function so we can patch the class
        # implementing the validation methods
        def mock_save_in_standardized_format(local_path, name, format):
            return resource_path, 'some_name'

        patched_ann_table_instance = AnnotationTable()
        patched_ann_table_instance.save_in_standardized_format = mock_save_in_standardized_format
        mock_get_resource_type_instance.side_effect = [
            # note that we don't need to patch this since GeneralResource instances
            # do not perform validation
            GeneralResource(),
            patched_ann_table_instance
        ]

        mock_get_local_resource_path.return_value = resource_path

        mock_move_resource_to_final_location.return_value = resource_path
        mock_f = mock.MagicMock()
        mock_f.get_local_resource_path.return_value = resource_path
        mock_get_storage_backend.return_value = mock_f

        r = Resource.objects.create(
            name = 'test_annotation_valid.tsv',
            owner = self.regular_user_1,
            is_active=True,
            path = resource_path,
            resource_type = '*'
        )
        validate_resource(r, '*', '')
        rm = ResourceMetadata.objects.get(resource=r)
        self.assertTrue(rm.observation_set is None)
        validate_resource(r, 'ANN', TSV_FORMAT)
        rm = ResourceMetadata.objects.get(resource=r)
        self.assertFalse(rm.observation_set is None)

    @mock.patch('api.utilities.resource_utilities.move_resource_to_final_location')
    @mock.patch('api.utilities.resource_utilities.get_storage_backend')
    @mock.patch('api.utilities.resource_utilities.check_file_format_against_type')
    @mock.patch('api.utilities.resource_utilities.get_resource_type_instance')
    @mock.patch('api.utilities.resource_utilities.get_local_resource_path')
    def test_metadata_when_type_changed_case2(self, mock_get_local_resource_path, \
        mock_get_resource_type_instance, \
        mock_check_file_format_against_type, \
        mock_get_storage_backend, mock_move_resource_to_final_location):

        resource_path = os.path.join(VAL_TESTDIR, 'test_matrix.tsv')
        mock_move_resource_to_final_location.return_value = resource_path
        mock_get_local_resource_path.return_value = resource_path

        # define this mock function so we can patch the class
        # implementing the validation methods
        def mock_save_in_standardized_format(local_path, name, format):
            return resource_path, 'some_name'

        patched_mtx_instance = Matrix()
        patched_mtx_instance.save_in_standardized_format = mock_save_in_standardized_format
        mock_get_resource_type_instance.side_effect = [
            # note that we don't need to patch this since GeneralResource instances
            # do not perform validation
            GeneralResource(),
            patched_mtx_instance
        ]
        mock_f = mock.MagicMock()
        mock_f.get_local_resource_path.return_value = resource_path
        mock_get_storage_backend.return_value = mock_f
        
        r = Resource.objects.create(
            name = 'test_matrix',
            owner = self.regular_user_1,
            is_active=True,
            path = resource_path,
            resource_type = '*'
        )
        validate_resource(r, '*', 'txt')
        rm = ResourceMetadata.objects.get(resource=r)
        self.assertTrue(rm.observation_set is None)
        validate_resource(r, 'MTX', TSV_FORMAT)
        rm = ResourceMetadata.objects.get(resource=r)
        obs_set = rm.observation_set
        samples = [x['id'] for x in obs_set['elements']]
        expected = ['SW1_Control','SW2_Control','SW3_Control','SW4_Treated','SW5_Treated','SW6_Treated']
        self.assertCountEqual(samples, expected)