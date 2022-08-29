import uuid
import os
import shutil
import json
import unittest.mock as mock

from django.urls import reverse
from django.core.exceptions import ImproperlyConfigured
from rest_framework import status
from rest_framework.exceptions import ValidationError
from django.conf import settings


from api.models import OperationResource, Operation
from constants import DATABASE_RESOURCE_TYPES, \
    TSV_FORMAT
from api.tests.base import BaseAPITestCase
from api.tests import test_settings

# the api/tests dir
TESTDIR = os.path.dirname(__file__)
TESTDIR = os.path.join(TESTDIR, 'resource_contents_test_files')


class OperationResourceViewTests(BaseAPITestCase):

    # The name for a directory relative to settings.MEDIA_ROOT
    TMP_TEST_DIR_NAME = 'tmp-tests'

    def setUp(self):
        self.establish_clients()

        ops = Operation.objects.all()
        if len(ops) == 0:
            raise ImproperlyConfigured('Need at least one Operation to run this')

        self.op = ops[0]

        # create some OperationResources for this Operation.
        # Need to point at real files. To avoid raising a SuspiciousOperation
        # exception, however, we need to copy to a location under our media root
        # Make the tmp dir:
        base_dir = settings.MEDIA_ROOT
        self.test_tmp_dir = os.path.join(base_dir, self.TMP_TEST_DIR_NAME)
        os.mkdir(self.test_tmp_dir)
        source_file = os.path.join(TESTDIR, 'demo_file1.tsv')
        shutil.copy(source_file, self.test_tmp_dir)

        testfile_path = os.path.join(
            self.test_tmp_dir, 
            os.path.basename(source_file)
        )
        op_r1 = OperationResource.objects.create(
            datafile = testfile_path,
            name = 'foo.txt',
            input_field = 'field_a',
            operation = self.op,
            resource_type = 'I_MTX',
            file_format = TSV_FORMAT
        )

        op_r2 = OperationResource.objects.create(
            datafile = testfile_path,
            name = 'bar.txt',
            input_field = 'field_a',
            operation = self.op,
            resource_type = 'MTX',
            file_format = TSV_FORMAT
        )

        op_r3 = OperationResource.objects.create(
            datafile = testfile_path,
            name = 'baz.txt',
            input_field = 'field_b',
            operation = self.op,
            resource_type = 'MTX',
            file_format = TSV_FORMAT
        )

    def tearDown(self):
        shutil.rmtree(self.test_tmp_dir)

    def test_list_resource_requires_auth(self):
        """
        Test that general requests to the endpoint generate 401
        """
        url = reverse('operation-resource-list', kwargs={'operation_uuid':uuid.uuid4()})
        response = self.regular_client.get(url)
        self.assertTrue((response.status_code == status.HTTP_401_UNAUTHORIZED) 
        | (response.status_code == status.HTTP_403_FORBIDDEN))

    def test_lists_all_fields(self):
        '''
        Tests that when we list the OperationResources for a specific operation,
        we get the OperationResources for ALL fields
        '''
        url = reverse('operation-resource-list', kwargs={'operation_uuid': self.op.pk})
        response = self.authenticated_regular_client.get(url)
        j = response.json()
        self.assertEqual(len(j), 3)

    def test_lists_with_bad_op_uuid(self):
        '''
        Tests 
        '''
        url = reverse('operation-resource-list', kwargs={'operation_uuid': uuid.uuid4()})
        response = self.authenticated_regular_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_lists_single_field(self):
        '''
        Tests that when we list the OperationResources for a specific operation
        and a single field, we get only the relevant resources
        '''
        url = reverse(
            'operation-resource-field-list', 
            kwargs={
                'operation_uuid': self.op.pk,
                'input_field': 'field_b'
            }
        )
        response = self.authenticated_regular_client.get(url)
        j = response.json()
        self.assertEqual(len(j), 1)
        self.assertEqual(j[0]['name'], 'baz.txt')

    def test_lists_single_field_given_bad_fieldname(self):
        '''
        Tests that when we ask for the operation resources for a non-existent
        field, we get zero responses. 
        '''
        url = reverse(
            'operation-resource-field-list', 
            kwargs={
                'operation_uuid': self.op.pk,
                'input_field': 'field_c'
            }
        )
        response = self.authenticated_regular_client.get(url)
        j = response.json()
        self.assertEqual(len(j), 0)