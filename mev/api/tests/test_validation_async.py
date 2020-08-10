import unittest
import unittest.mock as mock
import uuid
import random
import os

from django.core.exceptions import ImproperlyConfigured
from django.contrib.auth import get_user_model

from api.async_tasks import validate_resource, validate_resource_and_store
from api.models import Resource, ResourceMetadata
from resource_types import RESOURCE_MAPPING, \
    DB_RESOURCE_STRING_TO_HUMAN_READABLE, \
    OBSERVATION_SET_KEY, \
    FEATURE_SET_KEY, \
    PARENT_OP_KEY, \
    RESOURCE_KEY, \
    IntegerMatrix
from api.utilities.resource_utilities import handle_valid_resource
from api.tests.base import BaseAPITestCase
from resource_types import get_resource_type_instance

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
        with self.assertRaises(Resource.DoesNotExist):
            junk_uuid = uuid.uuid4()
            validate_resource(junk_uuid, 'MTX')

    def test_unknown_resource_type_raises_exception(self):
        '''
        If someone how an unknown resource type is passed to 
        the async validation function, raise an exception.

        Very unlikely, as the serializers will catch invalid
        payloads with bad resource_type specifications
        '''
        all_resources = Resource.objects.all()
        r = all_resources[0]
        with self.assertRaises(KeyError):
            validate_resource(r.pk, 'ABC')

    @mock.patch('api.utilities.resource_utilities.get_resource_type_instance')
    def test_invalid_type_remains_invalid_case1(self, mock_get_resource_type_instance):
        '''
        Here we test that a "unset" Resource (one where a resource_type
        has NEVER been set) remains unset if the validation fails
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

        mock_resource_instance = mock.MagicMock()
        mock_resource_instance.validate_type.return_value = (False, 'some string')
        mock_get_resource_type_instance.return_value = mock_resource_instance

        validate_resource(unset_resource.pk, 'MTX')

        # query the resource to see any changes:
        current_resource = Resource.objects.get(pk=unset_resource.pk)
        self.assertTrue(current_resource.is_active)
        self.assertIsNone(current_resource.resource_type)
        expected_status = Resource.FAILED.format(
            requested_resource_type = 'MTX'
        )
        self.assertEqual(current_resource.status, expected_status)

    @mock.patch('api.utilities.resource_utilities.check_extension')
    @mock.patch('api.utilities.resource_utilities.get_resource_type_instance')
    def test_invalid_type_remains_invalid_case2(self, mock_get_resource_type_instance,
        mock_check_extension):
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
        mock_resource_instance.validate_type.return_value = (False, 'some string')
        mock_get_resource_type_instance.return_value = mock_resource_instance
        mock_check_extension.return_value = True
        validate_resource(resource.pk, other_type)

        # query the resource to see any changes:
        current_resource = Resource.objects.get(pk=resource.pk)
        self.assertTrue(current_resource.is_active)
        self.assertEqual(current_resource.resource_type, current_type)
        expected_status = Resource.REVERTED.format(
            requested_resource_type = DB_RESOURCE_STRING_TO_HUMAN_READABLE[other_type],
            original_resource_type = DB_RESOURCE_STRING_TO_HUMAN_READABLE[current_type]
        )
        self.assertEqual(current_resource.status, expected_status)

    @mock.patch('api.utilities.resource_utilities.check_extension')
    @mock.patch('api.utilities.resource_utilities.move_resource_to_final_location')
    @mock.patch('api.utilities.resource_utilities.get_resource_type_instance')
    def test_resource_type_change_succeeds(self, 
        mock_get_resource_type_instance,
        mock_move,
        mock_check_extension):
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
        mock_resource_instance = mock.MagicMock()
        mock_resource_instance.validate_type.return_value = (True, 'some string')
        mock_resource_instance.extract_metadata.return_value = {
            PARENT_OP_KEY: None,
            OBSERVATION_SET_KEY: None,
            FEATURE_SET_KEY: None
        }
        mock_get_resource_type_instance.return_value = mock_resource_instance
        mock_check_extension.return_value = True       
        validate_resource(resource.pk, new_type)

        # query the resource to see any changes:
        current_resource = Resource.objects.get(pk=resource.pk)
        self.assertTrue(current_resource.is_active)
        self.assertEqual(current_resource.resource_type, new_type)
        self.assertFalse(current_resource.resource_type == original_type)
        self.assertEqual(current_resource.status, Resource.READY)

        mock_move.assert_not_called()

    @mock.patch('api.utilities.resource_utilities.check_extension')
    @mock.patch('api.utilities.resource_utilities.move_resource_to_final_location')
    @mock.patch('api.utilities.resource_utilities.get_resource_type_instance')
    def test_resource_type_change_succeeds_for_new_resource(self, 
        mock_get_resource_type_instance,
        mock_move,
        mock_check_extension):
        '''
        Here we test that a "unset" Resource (one where a resource_type
        has NEVER been set) changes once the validation succeeds
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
        mock_get_resource_type_instance.return_value = mock_resource_instance
        mock_check_extension.return_value = True
        
        fake_final_path = '/some/final_path/foo.tsv'
        mock_move.return_value = fake_final_path

        # call the tested function
        validate_resource_and_store(unset_resource.pk, 'MTX')

        # query the resource to see any changes:
        current_resource = Resource.objects.get(pk=unset_resource.pk)
        self.assertTrue(current_resource.is_active)
        self.assertEqual(current_resource.resource_type, 'MTX')
        self.assertEqual(current_resource.status, Resource.READY)
        self.assertEqual(current_resource.path, fake_final_path)

        mock_resource_instance.validate_type.assert_called()
        mock_resource_instance.extract_metadata.assert_called()


    @mock.patch('api.utilities.resource_utilities.move_resource_to_final_location')
    def test_resource_metadata_entered_in_db(self, 
        mock_move):
        '''
        Here we test that an instance of ResourceMetadata is created
        and tied to the appropriate resource.
        '''
        # create a Resource and give it our test integer matrix
        resource_path = os.path.join(TESTDIR, 'test_integer_matrix.tsv')
        resource_type = 'I_MTX'
        r = Resource.objects.create(
            path = resource_path,
            name = 'foo.tsv',
            resource_type = None,
            size = 1000,
            owner = get_user_model().objects.all()[0]
        )

        # check the original count for ResourceMetadata
        rm = ResourceMetadata.objects.filter(resource=r)
        n0 = len(rm)
        self.assertTrue(n0 == 0)

        # call the tested function
        resource_class_instance = get_resource_type_instance(resource_type)
        handle_valid_resource(r, resource_class_instance, resource_type)

        self.assertTrue(r.resource_type == resource_type)
        rm = ResourceMetadata.objects.filter(resource=r)
        n1 = len(rm)  
        self.assertTrue(n1 == 1)      

    @mock.patch('api.utilities.resource_utilities.move_resource_to_final_location')
    def test_resource_metadata_updated_in_db(self, 
        mock_move):
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
        r.save()

        # create a ResourceMetadata instance associated with that Resource
        ResourceMetadata.objects.create(
            resource=r,
            parent_operation = None,
            observation_set = None,
            feature_set = None
        )

        mock_move.return_value = resource_path

        # check the original count for ResourceMetadata
        rm = ResourceMetadata.objects.filter(resource=r)
        n0 = len(rm)
        self.assertEqual(n0, 1)
        rm_original = rm[0]

        # call the tested function
        validate_resource(r.pk, 'I_MTX')

        rm = ResourceMetadata.objects.filter(resource=r)
        n1 = len(rm)  

        # check that no new ResourceMetadata objects were created
        self.assertEqual(n1-n0, 0)
        rm_final = rm[0]
        
        # check that the observation_set changed as expected:
        self.assertFalse(rm_original.observation_set == rm_final.observation_set)


    @mock.patch('api.utilities.resource_utilities.settings')
    @mock.patch('api.utilities.resource_utilities.validate_resource')
    def test_storage_failure_handled_gracefully(self, 
        mock_validate_resource, mock_settings):
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
        
        mock_settings.RESOURCE_STORAGE_BACKEND.store.side_effect = Exception('problem!')

        # call the tested function
        validate_resource_and_store(unset_resource.pk, 'MTX')

        mock_validate_resource.assert_not_called()
        
        # query the resource to see any changes:
        current_resource = Resource.objects.get(pk=unset_resource.pk)
        self.assertTrue(current_resource.is_active)
        self.assertIsNone(current_resource.resource_type)
        self.assertEqual(current_resource.status, Resource.UNEXPECTED_STORAGE_ERROR)

    @mock.patch('api.utilities.resource_utilities.settings')
    @mock.patch('api.utilities.resource_utilities.get_resource_type_instance')
    @mock.patch('api.async_tasks.resource_utilities.move_resource_to_final_location')
    def test_validation_failure_handled_gracefully(self, 
        mock_move_resource_to_final_location,
        mock_get_resource_type_instance, mock_settings):
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
        mock_settings.RESOURCE_STORAGE_BACKEND.get_local_resource_path.return_value = '/some/path/bar.txt'

        # call the tested function
        validate_resource_and_store(unset_resource.pk, 'MTX')

        # query the resource to see any changes:
        current_resource = Resource.objects.get(pk=unset_resource.pk)
        self.assertTrue(current_resource.is_active)
        self.assertIsNone(current_resource.resource_type)
        self.assertEqual(current_resource.status, Resource.UNEXPECTED_VALIDATION_ERROR)