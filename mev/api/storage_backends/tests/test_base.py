import unittest.mock as mock
import os

from django.core.exceptions import ImproperlyConfigured

from api.tests.base import BaseAPITestCase
from api.models import Resource, OperationResource, Operation
from api.storage_backends.base import BaseStorageBackend


class TestBaseStorage(BaseAPITestCase):

    def test_resource_with_owner(self):
        '''
        Tests that the proper relative path (relative to the 
        storage root) is formed when we pass a Resource instance
        that has an owner
        '''

        owned_resources = Resource.objects.exclude(owner__isnull=True)
        chosen_resource = None
        for r in owned_resources:
            if r.owner:
                chosen_resource = r
                break
        if not chosen_resource:
            raise ImproperlyConfigured('Need at least one owned Resource'
                ' to run this test.'
            )

        p = BaseStorageBackend.construct_relative_path(r)
        expected_path = '{d}/{a}/{b}.{c}'.format(
            a = str(r.owner.pk),
            b = str(r.pk),
            c = r.name,
            d = Resource.USER_RESOURCE_STORAGE_DIRNAME
        )
        self.assertEqual(p, expected_path)

    def test_resource_without_owner(self):
        '''
        Tests that the proper relative path (relative to the 
        storage root) is formed when we pass a Resource instance
        that does NOT have an owner
        '''

        nonowned_resources = Resource.objects.filter(owner__isnull=True)
        if len(nonowned_resources) == 0:
            r = Resource.objects.create(
                name = 'foo.txt',
                path = '/a/b/foo.txt'
            )

        p = BaseStorageBackend.construct_relative_path(r)
        expected_path = '{a}/{b}.{c}'.format(
            a = Resource.OTHER_RESOURCE_STORAGE_DIRNAME,
            b = str(r.pk),
            c = r.name
        )
        self.assertEqual(p, expected_path)

    def test_operation_resource(self):

        ops = Operation.objects.all()
        if len(ops) == 0:
            raise ImproperlyConfigured('Need at least one Operation')
        else:
            op = ops[0]
            op_r = OperationResource.objects.create(
                operation = op,
                input_field = 'foo',
                name = 'abc.txt',
                path = '/a/b/abc.txt'
            )
            p = BaseStorageBackend.construct_relative_path(op_r)
            expected_path = '{d}/{a}/{b}.{c}'.format(
                a = str(op.pk),
                b = str(op_r.pk),
                c = op_r.name,
                d = OperationResource.OPERATION_RESOURCE_DIRNAME
            )
            self.assertEqual(p, expected_path)            
