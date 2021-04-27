import uuid
import os
import json
import unittest.mock as mock

from django.urls import reverse
from django.core.exceptions import ImproperlyConfigured
from rest_framework import status
from rest_framework.exceptions import ValidationError
from django.conf import settings


from api.models import OperationCategory, Operation
from api.tests.base import BaseAPITestCase
from api.tests import test_settings


def mocked_get_operation_instance_data(op):
    return {
        'id': str(op.id), 
        'name': op.name,
        'description': 'description',
        'repository_url': 'http://github.com',
        'git_hash': 'abc123',
        'mode': 'local_docker',
        'inputs': {},
        'outputs': {},
        'repo_name': 'repo-name',
        'workspace_operation': op.workspace_operation
    }

def add_objects():
    op1 = Operation.objects.create(
        active=True,
        name = 'DESeq2',
        successful_ingestion = True,
        workspace_operation = True
    )
    op2 = Operation.objects.create(
        active=True,
        name = 'Limma/Voom',
        successful_ingestion = True,
        workspace_operation = True
    )
    op3 = Operation.objects.create(
        active=True,
        name = 'Normalize',
        successful_ingestion = True,
        workspace_operation = True
    )

    op4 = Operation.objects.create(
        active=False,
        name = 'Normalize Old',
        successful_ingestion = True,
        workspace_operation = True
    )

    o1 = OperationCategory.objects.create(
        operation = op1,
        category = 'category_foo'
    )
    o2 = OperationCategory.objects.create(
        operation = op2,
        category = 'category_foo'
    )
    o3 = OperationCategory.objects.create(
        operation = op3,
        category = 'category_bar'
    )
    o3 = OperationCategory.objects.create(
        operation = op4,
        category = 'category_bar'
    )

class OperationCategoryListTests(BaseAPITestCase):

    def setUp(self):
        self.establish_clients()
        add_objects()

    @mock.patch('api.serializers.operation_category.get_operation_instance_data')
    def test_listing(self, mock_get_operation_instance_data):
        mock_get_operation_instance_data.side_effect = mocked_get_operation_instance_data
        url = reverse('operation-category-list')
        response = self.authenticated_admin_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        j = response.json()
        expected_mapping = {
            'category_foo': ['DESeq2','Limma/Voom'],
            'category_bar': ['Normalize']
        }
        expected_keys = ['category_foo','category_bar']
        self.assertCountEqual(expected_keys, [x['name'] for x in j])
        for obj in j:
            category_name = obj['name']
            op_list = obj['children']
            names = set([x['name'] for x in op_list])
            self.assertCountEqual(names, expected_mapping[category_name])
        # ensure that we did actually filter something out.
        # Above, we see that category_bar has only a single entry since one
        # of them was inactive and hence filtered out. This confirms that the
        # database HAD said object, but it was removed by the serializer due to the 
        # state of the "active" field
        ops = OperationCategory.objects.filter(category = 'category_bar')
        self.assertTrue(len(ops) == 2)


class OperationCategoryDetailTests(BaseAPITestCase):

    def setUp(self):
        self.establish_clients()
        add_objects()

    @mock.patch('api.views.operation_category_views.get_operation_instance_data')
    def test_details(self, mock_get_operation_instance_data):
        mock_get_operation_instance_data.side_effect = mocked_get_operation_instance_data
        url = reverse('operation-category-detail', kwargs={'category': 'category_foo'})
        response = self.authenticated_admin_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        j = response.json()
        names = set([x['name'] for x in j])
        self.assertCountEqual(names, ['DESeq2','Limma/Voom'])

    @mock.patch('api.views.operation_category_views.get_operation_instance_data')
    def test_empty_details(self, mock_get_operation_instance_data):
        mock_get_operation_instance_data.side_effect = mocked_get_operation_instance_data
        url = reverse('operation-category-detail', kwargs={'category': 'junk'})
        response = self.authenticated_admin_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        j = response.json()
        self.assertCountEqual(j,[])


class OperationCategoryAddTests(BaseAPITestCase):

    def setUp(self):
        self.establish_clients()

    def test_category_add(self):
        ops = Operation.objects.all()
        if len(ops) == 0:
            raise ImproperlyConfigured('Need at least one Operation to run this test.')

        initial_objects = OperationCategory.objects.all()
        n0 = len(initial_objects)

        url = reverse('operation-category-add')
        payload = {
            'operation_id': str(ops[0].id),
            'category': 'foo'
        }
        response = self.authenticated_admin_client.post(url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        final_objects = OperationCategory.objects.all()
        n1 = len(final_objects)
        self.assertEqual(1, n1-n0)

    def test_unknown_uuid(self):
        '''
        Test that a UUID corresponding to an unrecognized Operation fails
        '''
        initial_objects = OperationCategory.objects.all()
        n0 = len(initial_objects)

        url = reverse('operation-category-add')
        payload = {
            'operation_id': str(uuid.uuid4()),
            'category': 'foo'
        }
        response = self.authenticated_admin_client.post(url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        final_objects = OperationCategory.objects.all()
        n1 = len(final_objects)
        self.assertEqual(0, n1-n0)

    def test_bad_uuid(self):
        '''
        Test that an operation_id which is NOT a UUID fails
        '''
        initial_objects = OperationCategory.objects.all()
        n0 = len(initial_objects)

        url = reverse('operation-category-add')
        payload = {
            'operation_id': 'abc',
            'category': 'foo'
        }
        response = self.authenticated_admin_client.post(url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        final_objects = OperationCategory.objects.all()
        n1 = len(final_objects)
        self.assertEqual(0, n1-n0)