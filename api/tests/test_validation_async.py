import unittest
import unittest.mock as mock
import uuid
import random

from django.core.exceptions import ImproperlyConfigured

from api.async_tasks import validate_resource
from api.models import Resource
from api.resource_types import RESOURCE_MAPPING
from api.tests.base import BaseAPITestCase


class TestValidateResource(BaseAPITestCase):
    '''
    This tests that the proper things happen when we 
    call the asynchronous function to validate a Resource

    The actual validation and file relocation is mocked out
    but we check that the proper database objects are updated
    '''

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

    @mock.patch('api.async_tasks.resource_type_is_valid')
    def test_invalid_type_remains_invalid_case1(self, mock_resource_type_validation):
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

        mock_resource_type_validation.return_value = (False, 'some string')
        validate_resource(unset_resource.pk, 'MTX')

        # query the resource to see any changes:
        current_resource = Resource.objects.get(pk=unset_resource.pk)
        self.assertTrue(current_resource.is_active)
        self.assertIsNone(current_resource.resource_type)
        expected_status = Resource.FAILED.format(
            requested_resource_type = 'MTX'
        )
        self.assertEqual(current_resource.status, expected_status)

    @mock.patch('api.async_tasks.resource_type_is_valid')
    def test_invalid_type_remains_invalid_case2(self, mock_resource_type_validation):
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

        mock_resource_type_validation.return_value = (False, 'some string')
        validate_resource(resource.pk, other_type)

        # query the resource to see any changes:
        current_resource = Resource.objects.get(pk=resource.pk)
        self.assertTrue(current_resource.is_active)
        self.assertEqual(current_resource.resource_type, current_type)
        expected_status = Resource.REVERTED.format(
            requested_resource_type = other_type,
            original_resource_type = current_type
        )
        self.assertEqual(current_resource.status, expected_status)

    @mock.patch('api.async_tasks.move_resource_to_final_location')
    @mock.patch('api.async_tasks.resource_type_is_valid')
    def test_resource_type_change_succeeds(self, 
        mock_resource_type_validation,
        mock_move):
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

        # need to test the reversion of type, so need to know 
        # what it was in the first place.  We then randomly
        # choose a different type
        current_type = resource.resource_type
        new_type = current_type
        while new_type == current_type:
            new_type = random.choice(list(RESOURCE_MAPPING.keys()))

        mock_resource_type_validation.return_value = (True, 'some string')
        validate_resource(resource.pk, new_type)

        # query the resource to see any changes:
        current_resource = Resource.objects.get(pk=resource.pk)
        self.assertTrue(current_resource.is_active)
        self.assertEqual(current_resource.resource_type, new_type)
        self.assertEqual(current_resource.status, Resource.READY)

        mock_move.assert_not_called()

    @mock.patch('api.async_tasks.move_resource_to_final_location')
    @mock.patch('api.async_tasks.resource_type_is_valid')
    def test_resource_type_change_succeeds_for_new_resource(self, 
        mock_resource_type_validation,
        mock_move):
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

        # set the mock return values
        mock_resource_type_validation.return_value = (True, 'some string')
        fake_final_path = '/some/final_path/foo.tsv'
        mock_move.return_value = fake_final_path

        # call the tested function
        validate_resource(unset_resource.pk, 'MTX')

        # query the resource to see any changes:
        current_resource = Resource.objects.get(pk=unset_resource.pk)
        self.assertTrue(current_resource.is_active)
        self.assertEqual(current_resource.resource_type, 'MTX')
        self.assertEqual(current_resource.status, Resource.READY)
        self.assertEqual(current_resource.path, fake_final_path)
        mock_move.assert_called()