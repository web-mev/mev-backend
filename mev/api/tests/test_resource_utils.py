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
    WILDCARD, \
    UNSPECIFIED_FORMAT
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
from api.serializers.observation_set import ObservationSetSerializer
from api.utilities.resource_utilities import move_resource_to_final_location, \
    get_resource_view, \
    initiate_resource_validation, \
    handle_valid_resource, \
    handle_invalid_resource, \
    check_file_format_against_type, \
    add_metadata_to_resource, \
    get_resource_by_pk, \
    write_resource, \
    retrieve_resource_class_instance, \
    check_resource_request_validity, \
    delete_resource_by_pk, \
    localize_resource, \
    retrieve_metadata
from api.utilities.operations import read_operation_json, \
    check_for_resource_operations
from api.exceptions import NoResourceFoundException, \
    ResourceValidationException, \
    InactiveResourceException, \
    OwnershipException
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
        
    def get_unset_resource(self):
        all_resources = Resource.objects.all()
        unset_resources = []
        for r in all_resources:
            if not r.resource_type:
                unset_resources.append(r)
        
        if len(unset_resources) == 0:
            raise ImproperlyConfigured('Need at least one'
                ' Resource without a type to test properly.'
            )
        return unset_resources[0]

    @mock.patch('api.utilities.resource_utilities.get_resource_by_pk')
    def test_resource_request_validity(self, mock_get_resource_by_pk):
        '''
        Test that we receive the proper result when
        a api.models.Resource instance is requested.
        This function is used to ensure that users can only
        access their own Resource instances
        '''
        active_owned_resources = Resource.objects.filter(owner=self.regular_user_1, is_active=True)
        inactive_owned_resources = Resource.objects.filter(owner=self.regular_user_1, is_active=False)
        active_resource = active_owned_resources[0]
        inactive_resource = inactive_owned_resources[0]
        active_pk = str(active_resource.pk)
        inactive_pk = str(inactive_resource.pk)

        mock_get_resource_by_pk.return_value = active_resource
        result = check_resource_request_validity(self.regular_user_1, active_pk)
        self.assertEqual(active_resource, result)

        mock_get_resource_by_pk.return_value = inactive_resource
        with self.assertRaises(InactiveResourceException):
            result = check_resource_request_validity(self.regular_user_1, inactive_pk)

        mock_get_resource_by_pk.return_value = active_resource
        with self.assertRaises(OwnershipException):
            result = check_resource_request_validity(self.regular_user_2, active_pk)

        mock_get_resource_by_pk.side_effect = NoResourceFoundException
        with self.assertRaises(NoResourceFoundException):
            check_resource_request_validity(self.regular_user_1, active_pk)


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
            resource_type = 'MTX',
            file_format = TSV_FORMAT
        )
        r4 = get_resource_by_pk(r3.pk)
        self.assertEqual(r3,r4)

    @mock.patch('api.utilities.resource_utilities.alert_admins')
    @mock.patch('api.utilities.resource_utilities.get_resource_by_pk')
    def test_resource_delete(self, mock_get_resource_by_pk, mock_alert_admins):
        '''
        Tests that the function for deleting a database record works as expected
        '''
        # mock the simple/expected deletion
        mock_resource = mock.MagicMock()
        mock_get_resource_by_pk.return_value = mock_resource
        mock_pk = str(uuid.uuid4())
        delete_resource_by_pk(mock_pk)
        mock_get_resource_by_pk.assert_called_with(mock_pk)
        mock_resource.delete.assert_called()

        # mock that the resource was inactive. This function does NOT care about that.
        # Any deletion logic (e.g. disallowing for inactive files) should be implemented
        # prior to calling this function. Hence, the delete should succeed below:
        mock_resource = mock.MagicMock()
        mock_resource.is_active = False
        mock_get_resource_by_pk.return_value = mock_resource
        delete_resource_by_pk(mock_pk)
        mock_get_resource_by_pk.assert_called_with(mock_pk)
        mock_resource.delete.assert_called()

        # check that a database deletion failure will notify the admins
        mock_resource = mock.MagicMock()
        mock_resource.delete.side_effect = Exception('ack!')
        mock_get_resource_by_pk.return_value = mock_resource
        delete_resource_by_pk(mock_pk)
        mock_get_resource_by_pk.assert_called_with(mock_pk)
        mock_resource.delete.assert_called()
        mock_alert_admins.assert_called()

    @mock.patch('api.utilities.resource_utilities.get_storage_backend')
    def test_move_resource_to_final_location(self, mock_get_storage_backend):
        '''
        Tests that any/all exceptions raised by the backend's `store`
        method are caught and reported with a general Exception
        '''
        # check that we get back the expected path if the storage works:
        mock_storage_backend = mock.MagicMock()
        mock_path = '/ab/c/file.tsv'
        mock_storage_backend.store.return_value = mock_path
        mock_get_storage_backend.return_value = mock_storage_backend
        mock_resource = mock.MagicMock()
        result = move_resource_to_final_location(mock_resource)
        self.assertEqual(result, mock_path)

        # check that a specific exception is caught, but we report a generic one
        mock_storage_backend = mock.MagicMock()
        mock_storage_backend.store.side_effect = FileNotFoundError('nope!')
        mock_get_storage_backend.return_value = mock_storage_backend
        mock_resource = mock.MagicMock()
        with self.assertRaisesRegex(Exception, Resource.UNEXPECTED_STORAGE_ERROR):
            move_resource_to_final_location(mock_resource)

        # check that a generic error is caught and the message is altered:
        mock_storage_backend = mock.MagicMock()
        mock_storage_backend.store.side_effect = Exception('ack!')
        mock_get_storage_backend.return_value = mock_storage_backend
        mock_resource = mock.MagicMock()
        with self.assertRaisesRegex(Exception, Resource.UNEXPECTED_STORAGE_ERROR):
            move_resource_to_final_location(mock_resource)

    @mock.patch('api.utilities.resource_utilities.get_storage_backend')
    def test_localize_resource(self, mock_get_storage_backend):
        '''
        Tests that we execute properly and handle exceptions properly if the 
        torage backend encounters an issue
        '''
        # check the successful path:
        mock_path = '/some/mock/path.tsv'
        mock_storage_backend = mock.MagicMock()
        mock_storage_backend.localize_resource.return_value = mock_path
        mock_get_storage_backend.return_value = mock_storage_backend
        mock_resource = mock.MagicMock()
        self.assertEqual(mock_path, localize_resource(mock_resource))

        # check if the file was not found:
        mock_storage_backend = mock.MagicMock()
        mock_storage_backend.localize_resource.side_effect = FileNotFoundError('nope!')
        mock_get_storage_backend.return_value = mock_storage_backend
        mock_resource = mock.MagicMock()
        mock_resource.pk = 'xyz'
        mock_resource.path = mock_path
        with self.assertRaisesRegex(Exception, 'was not found'):
            localize_resource(mock_resource)

        # check if another exception was raised:
        mock_storage_backend = mock.MagicMock()
        mock_storage_backend.localize_resource.side_effect = Exception('something bad!')
        mock_get_storage_backend.return_value = mock_storage_backend
        mock_resource = mock.MagicMock()
        mock_resource.pk = 'xyz'
        mock_resource.path = mock_path
        with self.assertRaisesRegex(Exception, 'something bad!'):
            localize_resource(mock_resource)


    def test_retrieve_metadata(self):
        mock_resource_class_instance = mock.MagicMock()
        mock_metadata = {
            'mock_key': 'mock_value'
        }
        mock_resource_class_instance.extract_metadata.return_value = mock_metadata
        mock_path = '/some/mock/path.tsv'
        result = retrieve_metadata(mock_path, mock_resource_class_instance)
        self.assertDictEqual(result, mock_metadata)
        mock_resource_class_instance.extract_metadata.assert_called_with(mock_path)

        v = ValidationError({'key': 'val'})
        mock_resource_class_instance.extract_metadata.side_effect = v
        with self.assertRaisesRegex(ResourceValidationException, 'key:val') as ex:
            retrieve_metadata(mock_path, mock_resource_class_instance)

        mock_resource_class_instance.extract_metadata.side_effect = Exception('ack')
        with self.assertRaisesRegex(Exception, 'unexpected issue') as ex:
            retrieve_metadata(mock_path, mock_resource_class_instance)

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
        mock_storage_backend.localize_resource.return_value = '/foo'
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
        mock_storage_backend.localize_resource.assert_not_called()
        mock_get_contents.assert_not_called()

    @mock.patch('api.utilities.resource_utilities.retrieve_resource_class_instance')
    @mock.patch('api.utilities.resource_utilities.handle_invalid_resource')
    @mock.patch('api.utilities.resource_utilities.localize_resource')
    @mock.patch('api.utilities.resource_utilities.check_file_format_against_type')
    @mock.patch('api.utilities.resource_utilities.perform_validation')
    @mock.patch('api.utilities.resource_utilities.handle_valid_resource')
    def test_invalid_handler_called(self, mock_handle_valid_resource, \
            mock_perform_validation, \
            mock_check_file_format_against_type, \
            mock_localize_resource, \
            mock_handle_invalid_resource, \
            mock_retrieve_resource_class_instance):
        '''
        Here we test that a failure to validate the resource calls the proper
        handler function.
        '''
        unset_resource = self.get_unset_resource()

        mock_resource_class_instance = mock.MagicMock()
        mock_resource_class_instance.performs_validation.return_value = True
        mock_msg = 'some error message'
        mock_perform_validation.return_value = (False, mock_msg)
        mock_retrieve_resource_class_instance.return_value = mock_resource_class_instance

        initiate_resource_validation(unset_resource, 'MTX', 'csv')

        mock_handle_invalid_resource.assert_called_with(
            unset_resource,
            'MTX',
            'csv',
            mock_msg
        )
        mock_localize_resource.assert_called_with(unset_resource)
        mock_retrieve_resource_class_instance.assert_called_with('MTX')
        mock_handle_valid_resource.assert_not_called()

        # requery the resource
        r = Resource.objects.get(pk=unset_resource.pk)
        self.assertTrue(r.path == unset_resource.path)
        self.assertIsNone(r.resource_type)
        if unset_resource.file_format == '':
            self.assertEqual(r.file_format, '')
        else:
            self.assertIsNone(r.file_format)

    @mock.patch('api.utilities.resource_utilities.move_resource_to_final_location')
    @mock.patch('api.utilities.resource_utilities.retrieve_resource_class_instance')
    @mock.patch('api.utilities.resource_utilities.handle_invalid_resource')
    @mock.patch('api.utilities.resource_utilities.localize_resource')
    @mock.patch('api.utilities.resource_utilities.check_file_format_against_type')
    @mock.patch('api.utilities.resource_utilities.perform_validation')
    @mock.patch('api.utilities.resource_utilities.handle_valid_resource')
    def test_valid_handler_called(self, mock_handle_valid_resource, \
            mock_perform_validation, \
            mock_check_file_format_against_type, \
            mock_localize_resource, \
            mock_handle_invalid_resource, \
            mock_retrieve_resource_class_instance, \
            mock_move_resource_to_final_location):
        '''
        Here we test that a successful validation calls the proper
        handler function.
        '''
        unset_resource = self.get_unset_resource()

        mock_resource_class_instance = mock.MagicMock()
        mock_resource_class_instance.performs_validation.return_value = True
        mock_std_path = '/path/to/standardized.tsv'
        mock_resource_class_instance.save_in_standardized_format.return_value = mock_std_path
        mock_retrieve_resource_class_instance.return_value = mock_resource_class_instance

        mock_final_path = 'some/final/path.txt'
        mock_move_resource_to_final_location.return_value = mock_final_path

        mock_path = '/some/mock/path.txt'
        mock_localize_resource.return_value = mock_path
        
        mock_perform_validation.return_value = (True, None)

        initiate_resource_validation(unset_resource, 'MTX', TSV_FORMAT)

        mock_handle_valid_resource.assert_called_with(
            unset_resource,
            mock_resource_class_instance,
            mock_std_path
        )
        mock_handle_invalid_resource.assert_not_called()

        # requery the resource
        r = Resource.objects.get(pk=unset_resource.pk)
        self.assertTrue(r.path == mock_final_path)
        self.assertTrue(r.resource_type == 'MTX')
        self.assertTrue(r.file_format == TSV_FORMAT)

    @mock.patch('api.utilities.resource_utilities.retrieve_resource_class_instance')
    @mock.patch('api.utilities.resource_utilities.handle_valid_resource')
    @mock.patch('api.utilities.resource_utilities.handle_invalid_resource')
    @mock.patch('api.utilities.resource_utilities.check_file_format_against_type')
    def test_proper_exceptions_raised_case1(self, \
        mock_check_file_format_against_type, \
        mock_handle_invalid_resource, \
        mock_handle_valid_resource, \
        mock_retrieve_resource_class_instance):
        '''
        If unexpected errors (like connecting to cloud storage occur), check that we raise exceptions
        that provide helpful errors.

        Here, we test if the `check_file_format_against_type` function raises an exception. Note that if
        a predictable failure there (i.e. an inconsistent resource type and format were specified), then
        the function raises a ResourceValidationException. Since this exception is not expected, it is NOT
        of that type.
        '''
        mock_check_file_format_against_type.side_effect = [Exception('something unexpected!')]

        unset_resource = self.get_unset_resource()

        with self.assertRaisesRegex(Exception, 'something unexpected'):
            initiate_resource_validation(unset_resource, 'MTX', TSV_FORMAT)
        mock_handle_valid_resource.assert_not_called()
        mock_handle_invalid_resource.assert_not_called()
        mock_retrieve_resource_class_instance.assert_not_called()

    @mock.patch('api.utilities.resource_utilities.retrieve_resource_class_instance')
    @mock.patch('api.utilities.resource_utilities.handle_valid_resource')
    @mock.patch('api.utilities.resource_utilities.handle_invalid_resource')
    @mock.patch('api.utilities.resource_utilities.check_file_format_against_type')
    def test_proper_exceptions_raised_case2(self, \
        mock_check_file_format_against_type, \
        mock_handle_invalid_resource, \
        mock_handle_valid_resource, \
        mock_retrieve_resource_class_instance):
        '''
        If unexpected errors (like connecting to cloud storage occur), check that we raise exceptions
        that provide helpful errors.

        Here, we test if the `retrieve_resource_class_instance` function raises an exception from something
        unexpected
        '''
        mock_retrieve_resource_class_instance.side_effect = [Exception('ack'),]

        unset_resource = self.get_unset_resource()

        with self.assertRaisesRegex(Exception, 'ack'):
            initiate_resource_validation(unset_resource, 'MTX', TSV_FORMAT)
        mock_handle_valid_resource.assert_not_called()
        mock_handle_invalid_resource.assert_not_called()
        mock_retrieve_resource_class_instance.assert_called_with('MTX')


    @mock.patch('api.utilities.resource_utilities.retrieve_resource_class_instance')
    @mock.patch('api.utilities.resource_utilities.handle_valid_resource')
    @mock.patch('api.utilities.resource_utilities.handle_invalid_resource')
    @mock.patch('api.utilities.resource_utilities.check_file_format_against_type')
    def test_proper_exceptions_raised_case3(self, \
        mock_check_file_format_against_type, \
        mock_handle_invalid_resource, \
        mock_handle_valid_resource, \
        mock_retrieve_resource_class_instance):
        '''
        If unexpected errors (like connecting to cloud storage occur), check that we raise exceptions
        that provide helpful errors.

        Here, we test if the `retrieve_resource_class_instance` function raises an exception from an unknown
        resource type (a keyError). 
        '''
        mock_retrieve_resource_class_instance.side_effect = [KeyError('ZZZ'),]

        unset_resource = self.get_unset_resource()

        with self.assertRaisesRegex(Exception, 'ZZZ'):
            initiate_resource_validation(unset_resource, 'ZZZ', TSV_FORMAT)
        mock_handle_valid_resource.assert_not_called()
        mock_handle_invalid_resource.assert_not_called()
        mock_retrieve_resource_class_instance.assert_called_with('ZZZ')


    @mock.patch('api.utilities.resource_utilities.retrieve_resource_class_instance')
    @mock.patch('api.utilities.resource_utilities.perform_validation')
    @mock.patch('api.utilities.resource_utilities.localize_resource')
    @mock.patch('api.utilities.resource_utilities.check_file_format_against_type')
    def test_proper_exceptions_raised_case4(self, \
        mock_check_file_format_against_type, \
        mock_localize_resource, \
        mock_perform_validation, \
        mock_retrieve_resource_class_instance):
        '''
        If unexpected errors (like connecting to cloud storage occur), check that we raise exceptions
        that provide helpful errors.

        Here, we test if the localize_resource (a method of the storage backend) fails
        for some unexpected reason, such as failure to connect to cloud storage
        '''

        # here we mock there being a problem with the storage backend (maybe bucket storage
        # service is temporarily offline?)
        err_msg = 'something bad...'
        mock_localize_resource.side_effect = [Exception(err_msg)]

        mock_resource_class_instance = mock.MagicMock()
        mock_resource_class_instance.performs_validation.return_value = True
        mock_retrieve_resource_class_instance.return_value = mock_resource_class_instance

        unset_resource = self.get_unset_resource()

        with self.assertRaisesRegex(Exception, err_msg):
            initiate_resource_validation(unset_resource, 'MTX', TSV_FORMAT)
    
        mock_perform_validation.assert_not_called()

    @mock.patch('api.utilities.resource_utilities.handle_valid_resource')
    @mock.patch('api.utilities.resource_utilities.handle_invalid_resource')
    @mock.patch('api.utilities.resource_utilities.retrieve_resource_class_instance')
    @mock.patch('api.utilities.resource_utilities.perform_validation')
    @mock.patch('api.utilities.resource_utilities.localize_resource')
    @mock.patch('api.utilities.resource_utilities.check_file_format_against_type')
    def test_proper_exceptions_raised_case5(self, \
        mock_check_file_format_against_type, \
        mock_localize_resource, \
        mock_perform_validation, \
        mock_retrieve_resource_class_instance, \
        mock_handle_invalid_resource, \
        mock_handle_valid_resource):
        '''
        If unexpected errors (like connecting to cloud storage occur), check that we raise exceptions
        that provide helpful errors.

        Here, we test if the validation method fails unexpectedly.
        '''

        mock_resource_class_instance = mock.MagicMock()
        mock_resource_class_instance.performs_validation.return_value = True
        mock_retrieve_resource_class_instance.return_value = mock_resource_class_instance

        mock_local_path = '/some/local/path.txt'
        mock_localize_resource.return_value = mock_local_path

        err_msg = 'something unexpected.'
        mock_perform_validation.side_effect = [Exception(err_msg)]

        unset_resource = self.get_unset_resource()

        with self.assertRaisesRegex(Exception, err_msg):
            initiate_resource_validation(unset_resource, 'MTX', TSV_FORMAT)

        mock_perform_validation.assert_called_with(
            unset_resource,
            mock_resource_class_instance,
            TSV_FORMAT,
            mock_local_path
        )
        mock_handle_valid_resource.assert_not_called()
        mock_handle_invalid_resource.assert_not_called()

    def test_unset_resource_type_does_not_change_if_validation_fails(self):
        '''
        If we had previously validated a resource successfully, requesting
        a change that fails validation results in NO change to the resource_type
        attribute
        '''
        unset_resource = self.get_unset_resource()

        with self.assertRaises(ResourceMetadata.DoesNotExist):
            metadata = ResourceMetadata.objects.get(resource=unset_resource)

        handle_invalid_resource(unset_resource, 'MTX', TSV_FORMAT, 'some error message')
        self.assertIsNone(unset_resource.resource_type)

        # now the metadata query should succeed
        metadata = ResourceMetadata.objects.get(resource=unset_resource)
        metadata = ResourceMetadataSerializer(metadata).data
        self.assertIsNone(metadata[PARENT_OP_KEY])
        self.assertIsNone(metadata[OBSERVATION_SET_KEY])
        self.assertIsNone(metadata[FEATURE_SET_KEY])
        self.assertEqual(metadata[RESOURCE_KEY], unset_resource.pk)

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
        handle_invalid_resource(resource, other_type, TSV_FORMAT, 'some error message')

        # we don't query for an 'updated' Resource since the `handle_invalid_resource`
        # function doesn't save. It only updates attributes.
        self.assertTrue(resource.resource_type == original_type)
        self.assertTrue(resource.status.startswith(Resource.REVERTED.format(
            requested_resource_type=DB_RESOURCE_KEY_TO_HUMAN_READABLE[other_type],
            original_resource_type = DB_RESOURCE_KEY_TO_HUMAN_READABLE[original_type],
            requested_file_format = TSV_FORMAT,
            file_format = resource.file_format
            )
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


    @mock.patch('api.utilities.resource_utilities.retrieve_resource_class_instance')
    @mock.patch('api.utilities.resource_utilities.handle_valid_resource')
    @mock.patch('api.utilities.resource_utilities.check_file_format_against_type')
    @mock.patch('api.utilities.resource_utilities.move_resource_to_final_location')
    @mock.patch('api.utilities.resource_utilities.localize_resource')
    def test_proper_steps_taken_with_wildcard_resource(self, \
        mock_localize_resource, \
        mock_move_resource_to_final_location, \
        mock_check_file_format_against_type, \
        mock_handle_valid_resource, \
        mock_retrieve_resource_class_instance):
        '''
        Here we test that a esource type with a "wildcard" type goes through the proper
        steps. That is, we should skip the validation, etc.
        '''
        all_resources = Resource.objects.all()
        r = all_resources[0]
        initial_path = r.path

        g = GeneralResource()
        mock_retrieve_resource_class_instance.return_value = g
        mock_path = '/mock/final/path.txt'
        mock_move_resource_to_final_location.return_value = mock_path

        initiate_resource_validation(r, WILDCARD, UNSPECIFIED_FORMAT)

        mock_handle_valid_resource.assert_called_with(
            r, g, initial_path
        )

        mock_localize_resource.assert_not_called()

        r = Resource.objects.get(pk=r.pk)
        self.assertTrue(r.resource_type == WILDCARD)
        self.assertTrue(r.file_format == UNSPECIFIED_FORMAT)
        self.assertTrue(r.path == mock_path)

    def test_check_file_format_against_type_for_wildcard_resource(self):
        '''
        Checks that the type + format checking method just returns silently
        since we are trying to set to a wildcard/generic resource type
        '''
        self.assertIsNone(check_file_format_against_type(WILDCARD, ''))

    @mock.patch('api.utilities.resource_utilities.add_metadata_to_resource')
    @mock.patch('api.utilities.resource_utilities.retrieve_metadata')
    def test_check_handle_valid_resource_for_wildcard_type(self, \
        mock_retrieve_metadata, \
        mock_add_metadata_to_resource):
        '''
        Check that we do the proper things when we handle the apparently 
        "valid" resource. For wildcard types, they are trivially valid, but
        we need to check that we are not calling any methods that wouldn't 
        make sense in this context.
        '''
        mock_metadata = {
            'dummy_key': 'dummy_value'
        }
        mock_retrieve_metadata.return_value = mock_metadata

        all_resources = Resource.objects.all()
        r = all_resources[0]
        g = GeneralResource()
        handle_valid_resource(r, g, '')

        mock_retrieve_metadata.assert_called()
        mock_add_metadata_to_resource.assert_called_with(
            r,
            mock_metadata
        )

    @mock.patch('api.utilities.resource_utilities.retrieve_metadata')
    @mock.patch('api.utilities.resource_utilities.add_metadata_to_resource')
    def test_metadata_addition_failure(self, 
        mock_add_metadata_to_resource,
        mock_retrieve_metadata):
        '''
        Check that we do the proper things if the addition of the metadata
        to the resource fails.

        For instance, we had a case where the metadata extraction worked,
        but the sample IDs were too long. In that case, the `add_metadata_to_resource`
        function raised an uncaught exception and the Resource.path attribute
        was not set correctly.
        '''
        mock_metadata = {
            'mock_key': 'mock_val'
        }
        mock_retrieve_metadata.return_value = mock_metadata
        mock_add_metadata_to_resource.side_effect = ValidationError('ack')

        all_resources = Resource.objects.all()
        r = all_resources[0]
        mock_path = '/some/path/to/file.tsv'
        mock_resource_class_instance = mock.MagicMock()
        with self.assertRaisesRegex(Exception, 'ack'):
            handle_valid_resource(r, mock_resource_class_instance, mock_path)

        mock_add_metadata_to_resource.assert_called_with(
            r, mock_metadata
        )
        mock_retrieve_metadata.assert_called_with(mock_path, mock_resource_class_instance)

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
        # verify that the mock above is valid
        oss = ObservationSetSerializer(data=mock_obs_set)
        self.assertTrue(oss.is_valid())
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
        rm3 = ResourceMetadata.objects.get(resource=r)
        expected_obs_set = copy.deepcopy(mock_obs_set)
        elements = expected_obs_set['elements']
        for el in elements:
            el.update({'attributes': {}})
        self.assertEqual(rm3.observation_set['multiple'], mock_obs_set['multiple'])
        self.assertCountEqual(rm3.observation_set['elements'], elements)

    @mock.patch('api.utilities.resource_utilities.ResourceMetadataSerializer')
    @mock.patch('api.utilities.resource_utilities.alert_admins')
    def test_add_metadata_case2(self, mock_alert_admins, mock_serializer_cls):
        '''
        Test that we gracefully handle updates and save failures
        when associating metadata with a resource.

        Inspired by a runtime failure where the FeatureSet was too
        large for the database field. In such a case, we want to alert
        admins, but not stop a user from moving forward. Hence, we 
        recover from the failure by saving a bare-minimum metadata
        payload.
        '''
        # create a new Resource
        r = Resource.objects.create(
            name='foo.txt'
        )
        # ensure it has no associated metadata
        with self.assertRaises(ResourceMetadata.DoesNotExist):
            ResourceMetadata.objects.get(resource=r)

        # create some legitimate metadata to add. We ultimately 
        # mock there being a failure when trying to save this,
        # but we at least give it real data here
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
        # verify that the mock above is valid
        oss = ObservationSetSerializer(data=mock_obs_set)
        self.assertTrue(oss.is_valid())

        # create a mock object that will raise an exception
        from django.db.utils import OperationalError
        mock_serializer1 = mock.MagicMock()
        mock_serializer1.is_valid.return_value = True
        mock_serializer1.save.side_effect = OperationalError
        # The first time we ask for a ResourceMetadataSerializer, we mock
        # out the implementation so that we can fake an issue with its save
        # method. The second time, we use the actual class so we can verify
        # that we save only "basic" data in the event of an OperationalError
        basic_data = {
            RESOURCE_KEY: r.pk
        }
        real_instance = ResourceMetadataSerializer(data=basic_data)
        mock_serializer_cls.side_effect = [mock_serializer1, real_instance]
        add_metadata_to_resource(
            r, 
            {
                OBSERVATION_SET_KEY:mock_obs_set
            }
        )
        mock_alert_admins.assert_called()

        # check that we did actually persist the basic metadata to the db:
        rm = ResourceMetadata.objects.get(resource=r)
        rmd = ResourceMetadataSerializer(rm).data
        expected_metadata = {
            PARENT_OP_KEY: None,
            OBSERVATION_SET_KEY: None,
            FEATURE_SET_KEY: None,
            RESOURCE_KEY: r.pk
        }
        self.assertDictEqual(expected_metadata, rmd)

    @mock.patch('api.utilities.resource_utilities.ResourceMetadataSerializer')
    @mock.patch('api.utilities.resource_utilities.alert_admins')
    def test_add_metadata_case3(self, mock_alert_admins, mock_serializer_cls):
        '''
        Test that we gracefully handle updates and save failures
        when associating metadata with a resource.

        This covers the case where we encounter a generic Exception when
        trying to save the metadata. In such a case, we want to alert
        admins, but not stop a user from moving forward. Hence, we 
        recover from the failure by saving a bare-minimum metadata
        payload.
        '''
        # create a new Resource
        r = Resource.objects.create(
            name='foo.txt'
        )
        # ensure it has no associated metadata
        with self.assertRaises(ResourceMetadata.DoesNotExist):
            ResourceMetadata.objects.get(resource=r)

        # create some legitimate metadata to add. We ultimately 
        # mock there being a failure when trying to save this,
        # but we at least give it real data here
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
        # verify that the mock above is valid
        oss = ObservationSetSerializer(data=mock_obs_set)
        self.assertTrue(oss.is_valid())

        # create a mock object that will raise an exception
        mock_serializer1 = mock.MagicMock()
        mock_serializer1.is_valid.return_value = True
        mock_serializer1.save.side_effect = Exception('ack!')
        # The first time we ask for a ResourceMetadataSerializer, we mock
        # out the implementation so that we can fake an issue with its save
        # method. The second time, we use the actual class so we can verify
        # that we save only "basic" data in the event of an unexpected Exception
        basic_data = {
            RESOURCE_KEY: r.pk
        }
        real_instance = ResourceMetadataSerializer(data=basic_data)
        mock_serializer_cls.side_effect = [mock_serializer1, real_instance]
        add_metadata_to_resource(
            r, 
            {
                OBSERVATION_SET_KEY:mock_obs_set
            }
        )
        mock_alert_admins.assert_called()

        # check that we did actually persist the basic metadata to the db:
        rm = ResourceMetadata.objects.get(resource=r)
        rmd = ResourceMetadataSerializer(rm).data
        expected_metadata = {
            PARENT_OP_KEY: None,
            OBSERVATION_SET_KEY: None,
            FEATURE_SET_KEY: None,
            RESOURCE_KEY: r.pk
        }
        self.assertDictEqual(expected_metadata, rmd)


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
    @mock.patch('api.utilities.resource_utilities.check_file_format_against_type')
    @mock.patch('api.utilities.resource_utilities.retrieve_resource_class_instance')
    @mock.patch('api.utilities.resource_utilities.localize_resource')
    def test_metadata_when_type_changed(self, mock_localize_resource, \
        mock_retrieve_resource_class_instance, \
        mock_check_file_format_against_type, \
        mock_move_resource_to_final_location):
        '''
        Checks that the update of resource metadata is updated. Related to a bug where
        a file was initially set to a general type (and thus the metadata was effectively empty).
        After trying to validate it as an annotation type, it was raising json serializer errors.
        '''
        resource_path = os.path.join(VAL_TESTDIR, 'test_annotation_valid.tsv')

        # define this mock function so we can patch the class
        # implementing the validation methods
        def mock_save_in_standardized_format(local_path, format):
            return resource_path

        patched_ann_table_instance = AnnotationTable()
        patched_ann_table_instance.save_in_standardized_format = mock_save_in_standardized_format
        mock_retrieve_resource_class_instance.side_effect = [
            # note that we don't need to patch this since GeneralResource instances
            # do not perform validation
            GeneralResource(),
            patched_ann_table_instance
        ]

        mock_localize_resource.return_value = resource_path
        mock_move_resource_to_final_location.return_value = resource_path

        r = Resource.objects.create(
            name = 'test_annotation_valid.tsv',
            owner = self.regular_user_1,
            is_active=True,
            path = resource_path
        )
        initiate_resource_validation(r, WILDCARD, UNSPECIFIED_FORMAT)
        rm = ResourceMetadata.objects.get(resource=r)
        self.assertTrue(rm.observation_set is None)
        initiate_resource_validation(r, 'ANN', TSV_FORMAT)
        rm = ResourceMetadata.objects.get(resource=r)
        self.assertFalse(rm.observation_set is None)

    @mock.patch('api.utilities.resource_utilities.move_resource_to_final_location')
    @mock.patch('api.utilities.resource_utilities.check_file_format_against_type')
    @mock.patch('api.utilities.resource_utilities.retrieve_resource_class_instance')
    @mock.patch('api.utilities.resource_utilities.localize_resource')
    def test_metadata_when_type_changed_case2(self, mock_localize_resource, \
        mock_retrieve_resource_class_instance, \
        mock_check_file_format_against_type, \
        mock_move_resource_to_final_location):

        resource_path = os.path.join(VAL_TESTDIR, 'test_matrix.tsv')
        mock_move_resource_to_final_location.return_value = resource_path
        mock_localize_resource.return_value = resource_path

        # define this mock function so we can patch the class
        # implementing the validation methods
        def mock_save_in_standardized_format(local_path, format):
            return resource_path

        patched_mtx_instance = Matrix()
        patched_mtx_instance.save_in_standardized_format = mock_save_in_standardized_format
        mock_retrieve_resource_class_instance.side_effect = [
            # note that we don't need to patch this since GeneralResource instances
            # do not perform validation
            GeneralResource(),
            patched_mtx_instance
        ]
        mock_localize_resource.return_value = resource_path
        mock_move_resource_to_final_location.return_value = resource_path
        
        r = Resource.objects.create(
            name = 'test_matrix',
            owner = self.regular_user_1,
            is_active=True,
            path = resource_path,
        )
        initiate_resource_validation(r, WILDCARD, UNSPECIFIED_FORMAT)
        rm = ResourceMetadata.objects.get(resource=r)
        self.assertTrue(rm.observation_set is None)
        initiate_resource_validation(r, 'MTX', TSV_FORMAT)
        rm = ResourceMetadata.objects.get(resource=r)
        obs_set = rm.observation_set
        samples = [x['id'] for x in obs_set['elements']]
        expected = ['SW1_Control','SW2_Control','SW3_Control','SW4_Treated','SW5_Treated','SW6_Treated']
        self.assertCountEqual(samples, expected)

###########
# @mock.patch('api.utilities.resource_utilities.move_resource_to_final_location')
#     @mock.patch('api.utilities.resource_utilities.get_storage_backend')
#     def test_resource_metadata_entered_in_db(self,
#         mock_get_storage_backend, 
#         mock_move):
#         '''
#         Here we test that an instance of ResourceMetadata is created
#         and tied to the appropriate resource.
#         '''
#         # create a Resource and give it our test integer matrix
#         resource_path = os.path.join(TESTDIR, 'test_integer_matrix.tsv')

#         # note that we can't mock the class implementing the resource type, as
#         # we need its implementation to get the metadata. HOWEVER, we need to ensure
#         # that the file type above is ALREADY in the standardized format.
#         file_format = TSV_FORMAT
#         self.assertTrue(file_format == IntegerMatrix.STANDARD_FORMAT)

#         resource_type = 'I_MTX'
#         file_format = TSV_FORMAT
#         r = Resource.objects.create(
#             path = resource_path,
#             name = 'foo.tsv',
#             resource_type = INTEGER_MATRIX_KEY,
#             file_format = TSV_FORMAT,
#             size = 1000,
#             owner = get_user_model().objects.all()[0]
#         )

#         # check the original count for ResourceMetadata
#         rm = ResourceMetadata.objects.filter(resource=r)
#         n0 = len(rm)
#         self.assertTrue(n0 == 0)

#         # set some mock vals:
#         mock_storage_backend = mock.MagicMock()
#         mock_storage_backend.localize_resource.return_value = resource_path
#         mock_get_storage_backend.return_value = mock_storage_backend

#         # call the tested function
#         resource_class_instance = get_resource_type_instance(resource_type)
#         handle_valid_resource(r, resource_class_instance, resource_type, file_format)

#         self.assertTrue(r.resource_type == resource_type)
#         rm = ResourceMetadata.objects.filter(resource=r)
#         n1 = len(rm)  
#         self.assertTrue(n1 == 1)     

#         # since the file above is a TSV (which is the "standardized format" for a table)
#         mock_storage_backend.delete.assert_not_called() 

#     @mock.patch('api.utilities.resource_utilities.move_resource_to_final_location')
#     @mock.patch('api.utilities.resource_utilities.get_storage_backend')
#     @mock.patch('api.utilities.resource_utilities.check_file_format_against_type')
#     def test_resource_metadata_updated_in_db(self, mock_check_file_format_against_type, \
#         mock_get_storage_backend, mock_move):
#         '''
#         Here we test that an instance of ResourceMetadata is updated
#         when it previously existed (for instance, upon update of a
#         Resource type)
#         '''

#         # get one of the test resources (which has type of None):
#         rr = Resource.objects.filter(owner=self.regular_user_1, resource_type=None)
#         r = rr[0]

#         # give that Resource our test integer matrix
#         resource_path = os.path.join(TESTDIR, 'test_integer_matrix.tsv')
#         r.path = resource_path
#         r.name = 'test_integer_matris.tsv'
#         r.file_format = TSV_FORMAT
#         r.save()
#         # note that we can't mock the class implementing the resource type, as
#         # we need its implementation to get the metadata. HOWEVER, we need to ensure
#         # that the file type above is ALREADY in the standardized format.
#         self.assertTrue(r.file_format == IntegerMatrix.STANDARD_FORMAT)

#         # create a ResourceMetadata instance associated with that Resource
#         ResourceMetadata.objects.create(
#             resource=r,
#             parent_operation = None,
#             observation_set = None,
#             feature_set = None
#         )

#         mock_move.return_value = resource_path
#         mock_storage_backend = mock.MagicMock()
#         mock_storage_backend.localize_resource.return_value = resource_path
#         mock_get_storage_backend.return_value = mock_storage_backend

#         # check the original count for ResourceMetadata
#         rm = ResourceMetadata.objects.filter(resource=r)
#         n0 = len(rm)
#         self.assertEqual(n0, 1)
#         rm_original = rm[0]

#         # call the tested function
#         validate_resource(r.pk, 'I_MTX', TSV_FORMAT)

#         rm = ResourceMetadata.objects.filter(resource=r)
#         n1 = len(rm)  

#         # check that no new ResourceMetadata objects were created
#         self.assertEqual(n1-n0, 0)
#         rm_final = rm[0]
        
#         # check that the observation_set changed as expected:
#         self.assertFalse(rm_original.observation_set == rm_final.observation_set)

    # @mock.patch('api.utilities.resource_utilities.get_storage_backend')
    # @mock.patch('api.utilities.resource_utilities.initiate_resource_validation')
    # @mock.patch('api.utilities.resource_utilities.get_resource_size')
    # @mock.patch('api.async_tasks.async_resource_tasks.alert_admins')
    # def test_storage_failure_handled_gracefully(self,
    #     mock_alert_admins,
    #     mock_get_resource_size, 
    #     mock_initiate_resource_validation, mock_get_storage_backend):
    #     '''
    #     Here we test that we handle storage failures gracefully.

    #     In our workflow, newly uploaded files are pushed to the storage 
    #     "backend" before validating.  If we are dependent on an external 
    #     storage service (e.g. bucket), it is possible that this service
    #     could be unavailable or fail for some reason.  If an exception
    #     is raised, we want to set the appropriate fields on the Resource
    #     so that the Resource cannot be used.


    #     '''
    #     all_resources = Resource.objects.all()
    #     unset_resources = []
    #     for r in all_resources:
    #         if not r.resource_type:
    #             unset_resources.append(r)
        
    #     if len(unset_resources) == 0:
    #         raise ImproperlyConfigured('Need at least one'
    #             ' Resource without a type to test properly.'
    #         )

    #     unset_resource = unset_resources[0]
    #     self.assertIsNone(unset_resource.resource_type)
        
    #     mock_get_resource_size.return_value = 100

    #     mock_storage_backend = mock.MagicMock()
    #     mock_storage_backend.store.side_effect = Exception('problem!')
    #     mock_get_storage_backend.return_value = mock_storage_backend

    #     # call the tested function
    #     validate_resource_and_store(unset_resource.pk, 'MTX', TSV_FORMAT)

    #     mock_alert_admins.assert_called()
    #     mock_initiate_resource_validation.assert_not_called()
    #     mock_get_resource_size.assert_not_called()
        
    #     # query the resource to see any changes:
    #     current_resource = Resource.objects.get(pk=unset_resource.pk)
    #     self.assertFalse(current_resource.is_active)
    #     self.assertIsNone(current_resource.resource_type)
    #     self.assertEqual(current_resource.status, Resource.UNEXPECTED_STORAGE_ERROR)

    # @mock.patch('api.utilities.resource_utilities.check_file_format_against_type')
    # @mock.patch('api.utilities.resource_utilities.move_resource_to_final_location')
    # @mock.patch('api.utilities.resource_utilities.get_resource_type_instance')
    # @mock.patch('api.utilities.resource_utilities.get_storage_backend')
    # @mock.patch('api.utilities.resource_utilities.get_resource_size')
    # def test_resource_type_change_succeeds_for_new_resource_case2(self,
    #     mock_get_resource_size, 
    #     mock_get_storage_backend, 
    #     mock_get_resource_type_instance,
    #     mock_move,
    #     mock_check_file_format_against_type):
    #     '''
    #     Here we test that a "unset" Resource (one where a resource_type
    #     has NEVER been set) changes once the validation succeeds.

    #     Here, the "standardization" is trivial and hence no deletion is triggered
    #     '''
    #     all_resources = Resource.objects.all()
    #     unset_resources = []
    #     for r in all_resources:
    #         if not r.resource_type:
    #             unset_resources.append(r)
        
    #     if len(unset_resources) == 0:
    #         raise ImproperlyConfigured('Need at least one'
    #             ' Resource without a type to test properly.'
    #         )

    #     unset_resource = unset_resources[0]
    #     self.assertIsNone(unset_resource.resource_type)

    #     # set the mock return values
    #     mock_resource_instance = mock.MagicMock()
    #     mock_resource_instance.validate_type.return_value = (True, 'some string')
    #     mock_resource_instance.STANDARD_FORMAT = TSV_FORMAT
    #     mock_resource_instance.extract_metadata.return_value = {
    #         PARENT_OP_KEY: None,
    #         OBSERVATION_SET_KEY: None,
    #         FEATURE_SET_KEY: None
    #     }

    #     # given the strings below (which are the same as the original db Resource model), 
    #     # no deletion would be triggered (since the file is not changed by the standardization process)
    #     mock_resource_instance.save_in_standardized_format.return_value = (unset_resource.path,
    #         unset_resource.name)
    #     mock_get_resource_type_instance.return_value = mock_resource_instance
        
    #     fake_final_path = '/some/final_path/foo.tsv'
    #     mock_move.return_value = fake_final_path

    #     mock_storage_backend = mock.MagicMock()
    #     mock_storage_backend.localize_resource.return_value = unset_resource.path
    #     mock_get_storage_backend.return_value = mock_storage_backend

    #     mock_get_resource_size.return_value = 100

    #     # call the tested function
    #     validate_resource_and_store(unset_resource.pk, 'MTX', TSV_FORMAT)

    #     # query the resource to see any changes:
    #     current_resource = Resource.objects.get(pk=unset_resource.pk)
    #     self.assertTrue(current_resource.is_active)
    #     self.assertEqual(current_resource.resource_type, 'MTX')
    #     self.assertEqual(current_resource.status, Resource.READY)
    #     self.assertEqual(current_resource.path, fake_final_path)

    #     mock_resource_instance.validate_type.assert_called()
    #     mock_resource_instance.extract_metadata.assert_called()
    #     mock_storage_backend.delete.assert_not_called()

    #     @mock.patch('api.utilities.resource_utilities.get_storage_backend')
    # @mock.patch('api.utilities.resource_utilities.get_resource_type_instance')
    # @mock.patch('api.async_tasks.async_resource_tasks.resource_utilities.move_resource_to_final_location')
    # @mock.patch('api.utilities.resource_utilities.get_resource_size')
    # @mock.patch('api.utilities.resource_utilities.alert_admins')
    # @mock.patch('api.utilities.resource_utilities.check_file_format_against_type')
    # def test_validation_failure_handled_gracefully(self,
    #     mock_check_file_format_against_type, 
    #     mock_alert_admins,
    #     mock_get_resource_size,
    #     mock_move_resource_to_final_location,
    #     mock_get_resource_type_instance, mock_get_storage_backend):
    #     '''
    #     Here we test that we handle validation failures gracefully.
    #     '''
    #     all_resources = Resource.objects.all()
    #     unset_resources = []
    #     for r in all_resources:
    #         if not r.resource_type:
    #             unset_resources.append(r)
        
    #     if len(unset_resources) == 0:
    #         raise ImproperlyConfigured('Need at least one'
    #             ' Resource without a type to test properly.'
    #         )

    #     unset_resource = unset_resources[0]
    #     self.assertIsNone(unset_resource.resource_type)
    #     mock_move_resource_to_final_location.return_value = '/some/path.foo.txt'
    #     mock_resource_class_instance = mock.MagicMock()
    #     mock_resource_class_instance.validate_type.side_effect = Exception('validation ex!')
    #     mock_get_resource_type_instance.return_value = mock_resource_class_instance
    #     mock_storage_backend = mock.MagicMock()
    #     mock_storage_backend.localize_resource.return_value = '/some/path/bar.txt'
    #     mock_get_storage_backend.return_value = mock_storage_backend
    #     mock_get_resource_size.return_value = 100

    #     # call the tested function
    #     validate_resource_and_store(unset_resource.pk, 'MTX', TSV_FORMAT)
    #     mock_alert_admins.assert_called()

    #     # query the resource to see any changes:
    #     current_resource = Resource.objects.get(pk=unset_resource.pk)
    #     self.assertTrue(current_resource.is_active) # since an unexpected error was raised, don't activate
    #     self.assertIsNone(current_resource.resource_type)
    #     self.assertEqual(current_resource.status, Resource.UNEXPECTED_VALIDATION_ERROR)

# @mock.patch('api.utilities.resource_utilities.check_file_format_against_type')
#     @mock.patch('api.utilities.resource_utilities.get_resource_type_instance')
#     @mock.patch('api.utilities.resource_utilities.get_storage_backend')
#     def test_invalid_type_remains_invalid_case2(self, mock_get_storage_backend, mock_get_resource_type_instance,
#         mock_check_file_format_against_type):
#         '''
#         Here we test that a Resource change request fails.  The Resource previously
#         had a valid type (or it would not have been set) and we check that a failed
#         request "reverts" to the most recent valid resource type
#         '''
#         all_resources = Resource.objects.all()
#         set_resources = []
#         for r in all_resources:
#             if r.resource_type:
#                 set_resources.append(r)
        
#         if len(set_resources) == 0:
#             raise ImproperlyConfigured('Need at least one'
#                 ' Resource with a defined type to test properly.'
#             )

#         # just grab the first resource to use for the test
#         resource = set_resources[0]

#         # need to test the reversion of type, so need to know 
#         # what it was in the first place.  We then randomly
#         # choose a different type
#         current_type = resource.resource_type
#         other_type = current_type
#         while other_type == current_type:
#             other_type = random.choice(list(RESOURCE_MAPPING.keys()))

#         mock_resource_instance = mock.MagicMock()
#         failure_msg = 'Failed for this reason.'
#         mock_resource_instance.validate_type.return_value = (False, failure_msg)
#         mock_get_resource_type_instance.return_value = mock_resource_instance
#         validate_resource(resource.pk, other_type, TSV_FORMAT)

#         # query the resource to see any changes:
#         current_resource = Resource.objects.get(pk=resource.pk)
#         self.assertTrue(current_resource.is_active)
#         self.assertEqual(current_resource.resource_type, current_type)
#         expected_status = Resource.REVERTED.format(
#             requested_resource_type = DB_RESOURCE_KEY_TO_HUMAN_READABLE[other_type],
#             original_resource_type = DB_RESOURCE_KEY_TO_HUMAN_READABLE[current_type],
#             requested_file_format = TSV_FORMAT ,
#             file_format = current_resource.file_format
#         )
#         expected_status = expected_status + ' ' + failure_msg
#         self.assertEqual(current_resource.status, expected_status)

#     @mock.patch('api.utilities.resource_utilities.check_file_format_against_type')
#     @mock.patch('api.utilities.resource_utilities.move_resource_to_final_location')
#     @mock.patch('api.utilities.resource_utilities.get_resource_type_instance')
#     @mock.patch('api.utilities.resource_utilities.get_storage_backend')
#     def test_resource_type_change_succeeds(self, 
#         mock_get_storage_backend,
#         mock_get_resource_type_instance,
#         mock_move,
#         mock_check_file_format_against_type):
#         '''
#         Here we test that a Resource change request succeeds on a Resource
#         that had an existing type.
#         '''
#         all_resources = Resource.objects.all()
#         set_resources = []
#         for r in all_resources:
#             if r.resource_type:
#                 set_resources.append(r)
        
#         if len(set_resources) == 0:
#             raise ImproperlyConfigured('Need at least one'
#                 ' Resource with a defined type to test properly.'
#             )

#         # just grab the first resource to use for the test
#         resource = set_resources[0]

#         # Need to know 
#         # what it was in the first place.  We then randomly
#         # choose a different type
#         original_type = resource.resource_type
#         new_type = original_type
#         while new_type == original_type:
#             new_type = random.choice(list(RESOURCE_MAPPING.keys()))

#         # set the mock return values
#         new_path = '/some/mock/path.tsv'
#         mock_move.return_value = new_path
#         mock_resource_instance = mock.MagicMock()
#         mock_resource_instance.STANDARD_FORMAT = TSV_FORMAT
#         mock_resource_instance.validate_type.return_value = (True, 'some string')
#         mock_resource_instance.extract_metadata.return_value = {
#             PARENT_OP_KEY: None,
#             OBSERVATION_SET_KEY: None,
#             FEATURE_SET_KEY: None
#         }
#         mock_resource_instance.save_in_standardized_format.return_value = ('/some/path.txt', 'newname')
#         mock_get_resource_type_instance.return_value = mock_resource_instance
#         mock_storage_backend = mock.MagicMock()
#         mock_storage_backend.localize_resource.return_value = new_path
#         mock_get_storage_backend.return_value = mock_storage_backend
#         validate_resource(resource.pk, new_type, TSV_FORMAT)
        

#         # query the resource to see any changes:
#         current_resource = Resource.objects.get(pk=resource.pk)
#         self.assertTrue(current_resource.is_active)
#         self.assertEqual(current_resource.resource_type, new_type)
#         self.assertFalse(current_resource.resource_type == original_type)
#         self.assertEqual(current_resource.status, Resource.READY)
#         self.assertEqual(current_resource.path, new_path)
#         mock_move.assert_called()


#     @mock.patch('api.utilities.resource_utilities.check_file_format_against_type')
#     @mock.patch('api.utilities.resource_utilities.move_resource_to_final_location')
#     @mock.patch('api.utilities.resource_utilities.get_resource_type_instance')
#     @mock.patch('api.utilities.resource_utilities.get_storage_backend')
#     @mock.patch('api.utilities.resource_utilities.get_resource_size')
#     def test_resource_type_change_succeeds_for_new_resource_case1(self,
#         mock_get_resource_size,
#         mock_get_storage_backend, 
#         mock_get_resource_type_instance,
#         mock_move,
#         mock_check_file_format_against_type):
#         '''
#         Here we test that a "unset" Resource (one where a resource_type
#         has NEVER been set) changes once the validation succeeds

#         Here, the 'standardization' function changes the path, which
#         will test that the deletion method is called.
#         '''
#         all_resources = Resource.objects.all()
#         unset_resources = []
#         for r in all_resources:
#             if not r.resource_type:
#                 unset_resources.append(r)
        
#         if len(unset_resources) == 0:
#             raise ImproperlyConfigured('Need at least one'
#                 ' Resource without a type to test properly.'
#             )

#         unset_resource = unset_resources[0]
#         self.assertIsNone(unset_resource.resource_type)

#         # set the mock return values
#         mock_resource_instance = mock.MagicMock()
#         mock_resource_instance.validate_type.return_value = (True, 'some string')
#         mock_resource_instance.extract_metadata.return_value = {
#             PARENT_OP_KEY: None,
#             OBSERVATION_SET_KEY: None,
#             FEATURE_SET_KEY: None
#         }
#         mock_resource_instance.STANDARD_FORMAT = TSV_FORMAT


#         # given the strings below (which is different from the resource.path attr)
#         # that would trigger a delete as it's mocking there being an alteration
#         # of the path (as would happen if we saved in a standardized format)
#         mock_resource_instance.save_in_standardized_format.return_value = ('','')
#         mock_get_resource_type_instance.return_value = mock_resource_instance
        
#         fake_final_path = '/some/final_path/foo.tsv'
#         mock_move.return_value = fake_final_path

#         mock_storage_backend = mock.MagicMock()
#         mock_storage_backend.localize_resource.return_value = fake_final_path
#         mock_get_storage_backend.return_value = mock_storage_backend

#         mock_get_resource_size.return_value = 100

#         # call the tested function
#         validate_resource_and_store(unset_resource.pk, 'MTX', TSV_FORMAT)

#         # query the resource to see any changes:
#         current_resource = Resource.objects.get(pk=unset_resource.pk)
#         self.assertTrue(current_resource.is_active)
#         self.assertEqual(current_resource.resource_type, 'MTX')
#         self.assertEqual(current_resource.status, Resource.READY)
#         self.assertEqual(current_resource.path, fake_final_path)

#         mock_resource_instance.validate_type.assert_called()
#         mock_resource_instance.extract_metadata.assert_called()
#         mock_storage_backend.delete.assert_called()