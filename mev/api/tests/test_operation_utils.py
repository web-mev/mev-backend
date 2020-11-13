import unittest
import unittest.mock as mock
import os
import json
import copy
import uuid
import shutil

from django.core.exceptions import ImproperlyConfigured
from rest_framework.exceptions import ValidationError

from api.utilities.operations import read_operation_json, \
    validate_operation_inputs, \
    collect_resource_uuids
from api.tests.base import BaseAPITestCase
from api.models import Operation as OperationDbModel
from api.models import Workspace

# the api/tests dir
TESTDIR = os.path.dirname(__file__)
TESTDIR = os.path.join(TESTDIR, 'operation_test_files')

class OperationUtilsTester(BaseAPITestCase):

    def setUp(self):
        self.filepath = os.path.join(TESTDIR, 'valid_operation.json')
        fp = open(self.filepath)
        self.valid_dict = json.load(fp)
        fp.close()


        # the function we are testing requires an Operation database instance
        # Note, however, that we mock out the function that converts that into
        # the dictionary object describing the Operation. Hence, the actual
        # database instance we pass to the function does not matter.
        # Same goes for the Workspace (at least in this test).
        self.db_op = OperationDbModel.objects.create(id=uuid.uuid4())

        workspaces = Workspace.objects.all()
        if len(workspaces) == 0:
            raise ImproperlyConfigured('Need at least one Workspace to run this test.')
        self.workspace = workspaces[0]
        self.establish_clients()

    @mock.patch('api.utilities.operations.read_local_file')
    def test_read_operation_json(self, mock_read_local_file):

        # test that a properly formatted file returns 
        # a dict as expected:

        fp = open(self.filepath)
        mock_read_local_file.return_value = fp
        d = read_operation_json(self.filepath)
        self.assertDictEqual(d, self.valid_dict)

    @mock.patch('api.utilities.operations.get_operation_instance_data')
    def test_user_input_validation(self, mock_get_operation_instance_data):
        '''
        Test that we receive back an appropriate object following
        successful validation. All the inputs below are valid
        '''
        f = os.path.join(
            TESTDIR,
            'sample_for_basic_types_no_default.json'
        )
        d = read_operation_json(f)
        mock_get_operation_instance_data.return_value = d

        # some valid user inputs corresponding to the input specifications
        sample_inputs = {
            'int_no_default_type': 10, 
            'positive_int_no_default_type': 3, 
            'nonnegative_int_no_default_type': 0, 
            'bounded_int_no_default_type': 2, 
            'float_no_default_type':0.2, 
            'bounded_float_no_default_type': 0.4, 
            'positive_float_no_default_type': 0.01, 
            'nonnegative_float_no_default_type': 0.1, 
            'string_no_default_type': 'abc', 
            'boolean_no_default_type': True
        }

        workspaces = Workspace.objects.all()
        if len(workspaces) == 0:
            raise ImproperlyConfigured('Need at least one Workspace to run this test.')
        validate_operation_inputs(self.regular_user_1, 
            sample_inputs, self.db_op, self.workspace)

    @mock.patch('api.utilities.operations.get_operation_instance_data')
    def test_no_default_for_required_param(self, mock_get_operation_instance_data):
        '''
        Test that a missing required parameter triggers a validation error
        '''
        f = os.path.join(
            TESTDIR,
            'required_without_default.json'
        )
        d = read_operation_json(f)
        mock_get_operation_instance_data.return_value = d

        # one input was optional, one required. An empty payload
        # qualifies as a problem since it's missing the required key
        sample_inputs = {}

        with self.assertRaises(ValidationError):
            validate_operation_inputs(self.regular_user_1, 
                sample_inputs, self.db_op, self.workspace)

    @mock.patch('api.utilities.operations.get_operation_instance_data')
    def test_optional_value_filled_by_default(self, mock_get_operation_instance_data):
        '''
        Test that a missing optional parameter gets the default value
        '''
        f = os.path.join(
            TESTDIR,
            'required_without_default.json'
        )
        d = read_operation_json(f)
        mock_get_operation_instance_data.return_value = d

        # one input was optional, one required. An empty payload
        # qualifies as a problem since it's missing the required key
        sample_inputs = {'required_int_type': 22}

        final_inputs = validate_operation_inputs(self.regular_user_1, 
            sample_inputs, self.db_op, self.workspace)
        self.assertEqual(final_inputs['required_int_type'].submitted_value, 22)
        expected_default = d['inputs']['optional_int_type']['spec']['default']
        self.assertEqual(
            final_inputs['optional_int_type'].submitted_value, expected_default)

    @mock.patch('api.utilities.operations.get_operation_instance_data')
    def test_optional_value_overridden(self, mock_get_operation_instance_data):
        '''
        Test that the optional parameter is overridden when given
        '''
        f = os.path.join(
            TESTDIR,
            'required_without_default.json'
        )
        d = read_operation_json(f)
        mock_get_operation_instance_data.return_value = d

        sample_inputs = {
            'required_int_type': 22,
            'optional_int_type': 33
        }

        final_inputs = validate_operation_inputs(self.regular_user_1, 
            sample_inputs, self.db_op, self.workspace)
        self.assertEqual(final_inputs['required_int_type'].submitted_value, 22)
        self.assertEqual(final_inputs['optional_int_type'].submitted_value, 33)

    @mock.patch('api.utilities.operations.get_operation_instance_data')
    def test_optional_without_default_becomes_none(self, mock_get_operation_instance_data):
        '''
        Generally, Operations with optional inputs should have defaults. However,
        if that is violated, the "input" should be assigned to be None
        '''
        f = os.path.join(
            TESTDIR,
            'optional_without_default.json'
        )
        d = read_operation_json(f)
        mock_get_operation_instance_data.return_value = d

        # the only input is optional, so this is technically fine.
        sample_inputs = {}

        #with self.assertRaises(ValidationError):
        final_inputs = validate_operation_inputs(self.regular_user_1, 
            sample_inputs, self.db_op, self.workspace)
        self.assertIsNone(final_inputs['optional_int_type'])

    def test_collection_of_resource_uuids(self):
        '''
        To ensure that we don't erase crucial data resources in a workspace
        we have a utility function that scans through the executed operations
        of a workspace and returns a list of the "used" resource UUIDs.

        Here, we test that it returns the expected list
        '''
        # first test one where we expect an empty list-- no resources
        # are used or created:
        f = os.path.join(
            TESTDIR,
            'simple_op_test.json'
        )
        d = read_operation_json(f)
        mock_inputs = {
            'some_string': 'abc'
        }
        result = collect_resource_uuids(d['inputs'], mock_inputs)
        self.assertEqual(result, [])

        # test empty output/input dict:
        mock_outputs = {}
        result = collect_resource_uuids(d['outputs'], mock_outputs)
        self.assertEqual(result, [])

        # test a non-empty return
        f = os.path.join(
            TESTDIR,
            'valid_operation.json'
        )
        d = read_operation_json(f)
        mock_outputs = {
            'norm_counts': 'abc',
            'dge_table': 'xyz'
        }
        result = collect_resource_uuids(d['outputs'], mock_outputs)
        self.assertEqual(result, ['abc', 'xyz'])

        # test if there is some discrepancy in the expected and actual inputs
        # or outputs
        mock_outputs = {
            'junk': 'abc'
        }
        with self.assertRaises(Exception):
            result = collect_resource_uuids(d['outputs'], mock_outputs)
