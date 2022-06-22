import unittest
import unittest.mock as mock
import uuid
import random
import os

from django.core.exceptions import ImproperlyConfigured
from django.contrib.auth import get_user_model

from api.async_tasks.async_resource_tasks import validate_resource, validate_resource_and_store
from api.models import Resource, ResourceMetadata
from resource_types.base import DataResource
from resource_types import RESOURCE_MAPPING, IntegerMatrix

from constants import DB_RESOURCE_KEY_TO_HUMAN_READABLE, \
    OBSERVATION_SET_KEY, \
    FEATURE_SET_KEY, \
    PARENT_OP_KEY, \
    RESOURCE_KEY, \
    TSV_FORMAT
        
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
            validate_resource(junk_uuid, 'MTX', '')

    @mock.patch('api.async_tasks.async_resource_tasks.resource_utilities')
    @mock.patch('api.async_tasks.async_resource_tasks.alert_admins')
    def test_exception_handled(self, \
        mock_alert_admins, \
        mock_resource_utilities):
        '''
        If someone how an unknown resource type is passed to 
        the async validation function, raise an exception.

        Very unlikely, as the serializers will catch invalid
        payloads with bad resource_type specifications
        '''
        all_resources = Resource.objects.all()
        r = all_resources[0]
        mock_resource_utilities.get_resource_by_pk.return_value = r
        mock_resource_utilities.validate_resource.side_effect = [Exception('ex!')]

        validate_resource(r.pk, 'ABC', TSV_FORMAT)
        mock_alert_admins.assert_called_with('ex!')
        self.assertTrue(r.status == 'ex!')

    @mock.patch('api.utilities.resource_utilities.check_file_format_against_type')
    @mock.patch('api.utilities.resource_utilities.get_resource_type_instance')
    @mock.patch('api.utilities.resource_utilities.get_storage_backend')
    def test_invalid_type_remains_invalid_case2(self, mock_get_storage_backend, mock_get_resource_type_instance,
        mock_check_file_format_against_type):
        '''
        Here we test that a Resource change request fails.  The Resource previously
        had a valid type (or it would not have been set) and we check that a failed
        request "reverts" to the most recent valid resource type
        '''
        all_resources = Resource.objects.all()
        set_resources = []
        for r in all_resources:
            if r.resource_type:
                set_resources.append(r)
        
        if len(set_resources) == 0:
            raise ImproperlyConfigured('Need at least one'
                ' Resource with a defined type to test properly.'
            )

        # just grab the first resource to use for the test
        resource = set_resources[0]

        # need to test the reversion of type, so need to know 
        # what it was in the first place.  We then randomly
        # choose a different type
        current_type = resource.resource_type
        other_type = current_type
        while other_type == current_type:
            other_type = random.choice(list(RESOURCE_MAPPING.keys()))

        mock_resource_instance = mock.MagicMock()
        failure_msg = 'Failed for this reason.'
        mock_resource_instance.validate_type.return_value = (False, failure_msg)
        mock_get_resource_type_instance.return_value = mock_resource_instance
        validate_resource(resource.pk, other_type, TSV_FORMAT)

        # query the resource to see any changes:
        current_resource = Resource.objects.get(pk=resource.pk)
        self.assertTrue(current_resource.is_active)
        self.assertEqual(current_resource.resource_type, current_type)
        expected_status = Resource.REVERTED.format(
            requested_resource_type = DB_RESOURCE_KEY_TO_HUMAN_READABLE[other_type],
            original_resource_type = DB_RESOURCE_KEY_TO_HUMAN_READABLE[current_type]
        )
        expected_status = expected_status + ' ' + failure_msg
        self.assertEqual(current_resource.status, expected_status)

    @mock.patch('api.utilities.resource_utilities.check_file_format_against_type')
    @mock.patch('api.utilities.resource_utilities.move_resource_to_final_location')
    @mock.patch('api.utilities.resource_utilities.get_resource_type_instance')
    @mock.patch('api.utilities.resource_utilities.get_storage_backend')
    def test_resource_type_change_succeeds(self, 
        mock_get_storage_backend,
        mock_get_resource_type_instance,
        mock_move,
        mock_check_file_format_against_type):
        '''
        Here we test that a Resource change request succeeds on a Resource
        that had an existing type.
        '''
        all_resources = Resource.objects.all()
        set_resources = []
        for r in all_resources:
            if r.resource_type:
                set_resources.append(r)
        
        if len(set_resources) == 0:
            raise ImproperlyConfigured('Need at least one'
                ' Resource with a defined type to test properly.'
            )

        # just grab the first resource to use for the test
        resource = set_resources[0]

        # Need to know 
        # what it was in the first place.  We then randomly
        # choose a different type
        original_type = resource.resource_type
        new_type = original_type
        while new_type == original_type:
            new_type = random.choice(list(RESOURCE_MAPPING.keys()))

        # set the mock return values
        new_path = '/some/mock/path.tsv'
        mock_move.return_value = new_path
        mock_resource_instance = mock.MagicMock()
        mock_resource_instance.STANDARD_FORMAT = TSV_FORMAT
        mock_resource_instance.validate_type.return_value = (True, 'some string')
        mock_resource_instance.extract_metadata.return_value = {
            PARENT_OP_KEY: None,
            OBSERVATION_SET_KEY: None,
            FEATURE_SET_KEY: None
        }
        mock_resource_instance.save_in_standardized_format.return_value = ('/some/path.txt', 'newname')
        mock_get_resource_type_instance.return_value = mock_resource_instance
        mock_storage_backend = mock.MagicMock()
        mock_storage_backend.get_local_resource_path.return_value = new_path
        mock_get_storage_backend.return_value = mock_storage_backend
        validate_resource(resource.pk, new_type, TSV_FORMAT)
        

        # query the resource to see any changes:
        current_resource = Resource.objects.get(pk=resource.pk)
        self.assertTrue(current_resource.is_active)
        self.assertEqual(current_resource.resource_type, new_type)
        self.assertFalse(current_resource.resource_type == original_type)
        self.assertEqual(current_resource.status, Resource.READY)
        self.assertEqual(current_resource.path, new_path)
        mock_move.assert_called()


    @mock.patch('api.utilities.resource_utilities.check_file_format_against_type')
    @mock.patch('api.utilities.resource_utilities.move_resource_to_final_location')
    @mock.patch('api.utilities.resource_utilities.get_resource_type_instance')
    @mock.patch('api.utilities.resource_utilities.get_storage_backend')
    @mock.patch('api.utilities.resource_utilities.get_resource_size')
    def test_resource_type_change_succeeds_for_new_resource_case1(self,
        mock_get_resource_size,
        mock_get_storage_backend, 
        mock_get_resource_type_instance,
        mock_move,
        mock_check_file_format_against_type):
        '''
        Here we test that a "unset" Resource (one where a resource_type
        has NEVER been set) changes once the validation succeeds

        Here, the 'standardization' function changes the path, which
        will test that the deletion method is called.
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
        self.assertIsNone(unset_resource.resource_type)

        # set the mock return values
        mock_resource_instance = mock.MagicMock()
        mock_resource_instance.validate_type.return_value = (True, 'some string')
        mock_resource_instance.extract_metadata.return_value = {
            PARENT_OP_KEY: None,
            OBSERVATION_SET_KEY: None,
            FEATURE_SET_KEY: None
        }
        mock_resource_instance.STANDARD_FORMAT = TSV_FORMAT


        # given the strings below (which is different from the resource.path attr)
        # that would trigger a delete as it's mocking there being an alteration
        # of the path (as would happen if we saved in a standardized format)
        mock_resource_instance.save_in_standardized_format.return_value = ('','')
        mock_get_resource_type_instance.return_value = mock_resource_instance
        
        fake_final_path = '/some/final_path/foo.tsv'
        mock_move.return_value = fake_final_path

        mock_storage_backend = mock.MagicMock()
        mock_storage_backend.get_local_resource_path.return_value = fake_final_path
        mock_get_storage_backend.return_value = mock_storage_backend

        mock_get_resource_size.return_value = 100

        # call the tested function
        validate_resource_and_store(unset_resource.pk, 'MTX', TSV_FORMAT)

        # query the resource to see any changes:
        current_resource = Resource.objects.get(pk=unset_resource.pk)
        self.assertTrue(current_resource.is_active)
        self.assertEqual(current_resource.resource_type, 'MTX')
        self.assertEqual(current_resource.status, Resource.READY)
        self.assertEqual(current_resource.path, fake_final_path)

        mock_resource_instance.validate_type.assert_called()
        mock_resource_instance.extract_metadata.assert_called()
        mock_storage_backend.delete.assert_called()

    @mock.patch('api.utilities.resource_utilities.check_file_format_against_type')
    @mock.patch('api.utilities.resource_utilities.move_resource_to_final_location')
    @mock.patch('api.utilities.resource_utilities.get_resource_type_instance')
    @mock.patch('api.utilities.resource_utilities.get_storage_backend')
    @mock.patch('api.utilities.resource_utilities.get_resource_size')
    def test_resource_type_change_succeeds_for_new_resource_case2(self,
        mock_get_resource_size, 
        mock_get_storage_backend, 
        mock_get_resource_type_instance,
        mock_move,
        mock_check_file_format_against_type):
        '''
        Here we test that a "unset" Resource (one where a resource_type
        has NEVER been set) changes once the validation succeeds.

        Here, the "standardization" is trivial and hence no deletion is triggered
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
        self.assertIsNone(unset_resource.resource_type)

        # set the mock return values
        mock_resource_instance = mock.MagicMock()
        mock_resource_instance.validate_type.return_value = (True, 'some string')
        mock_resource_instance.STANDARD_FORMAT = TSV_FORMAT
        mock_resource_instance.extract_metadata.return_value = {
            PARENT_OP_KEY: None,
            OBSERVATION_SET_KEY: None,
            FEATURE_SET_KEY: None
        }

        # given the strings below (which are the same as the original db Resource model), 
        # no deletion would be triggered (since the file is not changed by the standardization process)
        mock_resource_instance.save_in_standardized_format.return_value = (unset_resource.path,
            unset_resource.name)
        mock_get_resource_type_instance.return_value = mock_resource_instance
        
        fake_final_path = '/some/final_path/foo.tsv'
        mock_move.return_value = fake_final_path

        mock_storage_backend = mock.MagicMock()
        mock_storage_backend.get_local_resource_path.return_value = unset_resource.path
        mock_get_storage_backend.return_value = mock_storage_backend

        mock_get_resource_size.return_value = 100

        # call the tested function
        validate_resource_and_store(unset_resource.pk, 'MTX', TSV_FORMAT)

        # query the resource to see any changes:
        current_resource = Resource.objects.get(pk=unset_resource.pk)
        self.assertTrue(current_resource.is_active)
        self.assertEqual(current_resource.resource_type, 'MTX')
        self.assertEqual(current_resource.status, Resource.READY)
        self.assertEqual(current_resource.path, fake_final_path)

        mock_resource_instance.validate_type.assert_called()
        mock_resource_instance.extract_metadata.assert_called()
        mock_storage_backend.delete.assert_not_called()


    @mock.patch('api.utilities.resource_utilities.move_resource_to_final_location')
    @mock.patch('api.utilities.resource_utilities.get_storage_backend')
    def test_resource_metadata_entered_in_db(self,
        mock_get_storage_backend, 
        mock_move):
        '''
        Here we test that an instance of ResourceMetadata is created
        and tied to the appropriate resource.
        '''
        # create a Resource and give it our test integer matrix
        resource_path = os.path.join(TESTDIR, 'test_integer_matrix.tsv')

        # note that we can't mock the class implementing the resource type, as
        # we need its implementation to get the metadata. HOWEVER, we need to ensure
        # that the file type above is ALREADY in the standardized format.
        file_format = TSV_FORMAT
        self.assertTrue(file_format == IntegerMatrix.STANDARD_FORMAT)

        resource_type = 'I_MTX'
        file_format = TSV_FORMAT
        r = Resource.objects.create(
            path = resource_path,
            name = 'foo.tsv',
            resource_type = None,
            file_format = TSV_FORMAT,
            size = 1000,
            owner = get_user_model().objects.all()[0]
        )

        # check the original count for ResourceMetadata
        rm = ResourceMetadata.objects.filter(resource=r)
        n0 = len(rm)
        self.assertTrue(n0 == 0)

        # set some mock vals:
        mock_storage_backend = mock.MagicMock()
        mock_storage_backend.get_local_resource_path.return_value = resource_path
        mock_get_storage_backend.return_value = mock_storage_backend

        # call the tested function
        resource_class_instance = get_resource_type_instance(resource_type)
        handle_valid_resource(r, resource_class_instance, resource_type, file_format)

        self.assertTrue(r.resource_type == resource_type)
        rm = ResourceMetadata.objects.filter(resource=r)
        n1 = len(rm)  
        self.assertTrue(n1 == 1)     

        # since the file above is a TSV (which is the "standardized format" for a table)
        mock_storage_backend.delete.assert_not_called() 

    @mock.patch('api.utilities.resource_utilities.move_resource_to_final_location')
    @mock.patch('api.utilities.resource_utilities.get_storage_backend')
    @mock.patch('api.utilities.resource_utilities.check_file_format_against_type')
    def test_resource_metadata_updated_in_db(self, mock_check_file_format_against_type, \
        mock_get_storage_backend, mock_move):
        '''
        Here we test that an instance of ResourceMetadata is updated
        when it previously existed (for instance, upon update of a
        Resource type)
        '''

        # get one of the test resources (which has type of None):
        rr = Resource.objects.filter(owner=self.regular_user_1, resource_type=None)
        r = rr[0]

        # give that Resource our test integer matrix
        resource_path = os.path.join(TESTDIR, 'test_integer_matrix.tsv')
        r.path = resource_path
        r.name = 'test_integer_matris.tsv'
        r.file_format = TSV_FORMAT
        r.save()
        # note that we can't mock the class implementing the resource type, as
        # we need its implementation to get the metadata. HOWEVER, we need to ensure
        # that the file type above is ALREADY in the standardized format.
        self.assertTrue(r.file_format == IntegerMatrix.STANDARD_FORMAT)

        # create a ResourceMetadata instance associated with that Resource
        ResourceMetadata.objects.create(
            resource=r,
            parent_operation = None,
            observation_set = None,
            feature_set = None
        )

        mock_move.return_value = resource_path
        mock_storage_backend = mock.MagicMock()
        mock_storage_backend.get_local_resource_path.return_value = resource_path
        mock_get_storage_backend.return_value = mock_storage_backend

        # check the original count for ResourceMetadata
        rm = ResourceMetadata.objects.filter(resource=r)
        n0 = len(rm)
        self.assertEqual(n0, 1)
        rm_original = rm[0]

        # call the tested function
        validate_resource(r.pk, 'I_MTX', TSV_FORMAT)

        rm = ResourceMetadata.objects.filter(resource=r)
        n1 = len(rm)  

        # check that no new ResourceMetadata objects were created
        self.assertEqual(n1-n0, 0)
        rm_final = rm[0]
        
        # check that the observation_set changed as expected:
        self.assertFalse(rm_original.observation_set == rm_final.observation_set)


    @mock.patch('api.utilities.resource_utilities.get_storage_backend')
    @mock.patch('api.utilities.resource_utilities.validate_resource')
    @mock.patch('api.utilities.resource_utilities.get_resource_size')
    @mock.patch('api.async_tasks.async_resource_tasks.alert_admins')
    def test_storage_failure_handled_gracefully(self,
        mock_alert_admins,
        mock_get_resource_size, 
        mock_validate_resource, mock_get_storage_backend):
        '''
        Here we test that we handle storage failures gracefully.

        In our workflow, newly uploaded files are pushed to the storage 
        "backend" before validating.  If we are dependent on an external 
        storage service (e.g. bucket), it is possible that this service
        could be unavailable or fail for some reason.  If an exception
        is raised, we want to set the appropriate fields on the Resource
        so that the Resource cannot be used.


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
        self.assertIsNone(unset_resource.resource_type)
        
        mock_get_resource_size.return_value = 100

        mock_storage_backend = mock.MagicMock()
        mock_storage_backend.store.side_effect = Exception('problem!')
        mock_get_storage_backend.return_value = mock_storage_backend

        # call the tested function
        validate_resource_and_store(unset_resource.pk, 'MTX', TSV_FORMAT)

        mock_alert_admins.assert_called()
        mock_validate_resource.assert_not_called()
        mock_get_resource_size.assert_not_called()
        
        # query the resource to see any changes:
        current_resource = Resource.objects.get(pk=unset_resource.pk)
        self.assertFalse(current_resource.is_active)
        self.assertIsNone(current_resource.resource_type)
        self.assertEqual(current_resource.status, Resource.UNEXPECTED_STORAGE_ERROR)

    @mock.patch('api.utilities.resource_utilities.get_storage_backend')
    @mock.patch('api.utilities.resource_utilities.get_resource_type_instance')
    @mock.patch('api.async_tasks.async_resource_tasks.resource_utilities.move_resource_to_final_location')
    @mock.patch('api.utilities.resource_utilities.get_resource_size')
    @mock.patch('api.utilities.resource_utilities.alert_admins')
    @mock.patch('api.utilities.resource_utilities.check_file_format_against_type')
    def test_validation_failure_handled_gracefully(self,
        mock_check_file_format_against_type, 
        mock_alert_admins,
        mock_get_resource_size,
        mock_move_resource_to_final_location,
        mock_get_resource_type_instance, mock_get_storage_backend):
        '''
        Here we test that we handle validation failures gracefully.
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
        self.assertIsNone(unset_resource.resource_type)
        mock_move_resource_to_final_location.return_value = '/some/path.foo.txt'
        mock_resource_class_instance = mock.MagicMock()
        mock_resource_class_instance.validate_type.side_effect = Exception('validation ex!')
        mock_get_resource_type_instance.return_value = mock_resource_class_instance
        mock_storage_backend = mock.MagicMock()
        mock_storage_backend.get_local_resource_path.return_value = '/some/path/bar.txt'
        mock_get_storage_backend.return_value = mock_storage_backend
        mock_get_resource_size.return_value = 100

        # call the tested function
        validate_resource_and_store(unset_resource.pk, 'MTX', TSV_FORMAT)
        mock_alert_admins.assert_called()

        # query the resource to see any changes:
        current_resource = Resource.objects.get(pk=unset_resource.pk)
        self.assertTrue(current_resource.is_active) # since an unexpected error was raised, don't activate
        self.assertIsNone(current_resource.resource_type)
        self.assertEqual(current_resource.status, Resource.UNEXPECTED_VALIDATION_ERROR)