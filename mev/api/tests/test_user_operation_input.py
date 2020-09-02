import unittest
import unittest.mock as mock
import os
import json
import copy
import uuid
import shutil

from django.core.exceptions import ImproperlyConfigured
from rest_framework.exceptions import ValidationError

from api.utilities.operations import read_operation_json
from api.data_structures.user_operation_input import user_operation_input_mapping
from api.models import Resource
from api.tests.base import BaseAPITestCase

from resource_types import RESOURCE_MAPPING

# the api/tests dir
TESTDIR = os.path.dirname(__file__)
TESTDIR = os.path.join(TESTDIR, 'operation_test_files')

class UserOperationInputTester(BaseAPITestCase):

    def setUp(self):
        self.filepath = os.path.join(TESTDIR, 'valid_operation.json')
        fp = open(self.filepath)
        self.valid_dict = json.load(fp)
        fp.close()

        self.establish_clients()

    @mock.patch('api.utilities.operations.read_local_file')
    def test_read_operation_json(self, mock_read_local_file):

        # test that a properly formatted file returns 
        # a dict as expected:

        fp = open(self.filepath)
        mock_read_local_file.return_value = fp
        d = read_operation_json(self.filepath)
        self.assertDictEqual(d, self.valid_dict)

    def test_basic_user_inputs(self):
        '''
        This tests that the proper validation happens
        when comparing the user-submitted values and the input
        specifications. Here, the values are all valid.
        '''
        f = os.path.join(
            TESTDIR,
            'sample_for_basic_types.json'
        )
        d = read_operation_json(f)

        # some valid user inputs corresponding to the input specifications
        sample_inputs = {
            'int_type': 10, 
            'positive_int_type': 3, 
            'nonnegative_int_type': 0, 
            'bounded_int_type': 2, 
            'float_type':0.2, 
            'bounded_float_type': 0.4, 
            'positive_float_type': 0.01, 
            'nonnegative_float_type': 0.1, 
            'string_type': 'abc', 
            'boolean_type': True
        }

        for key, val in sample_inputs.items():
            spec_object = d['inputs'][key]['spec']
            spec_type = spec_object['attribute_type']
            user_operation_input_class = user_operation_input_mapping[spec_type]
            user_operation_input_class(self.regular_user_1, key, val, spec_object)

    def test_bad_basic_user_inputs(self):
        '''
        This tests that the proper validation happens
        when comparing the user-submitted values and the input
        specifications. Here, the user inputs violate the type
        constraints
        '''
        f = os.path.join(
            TESTDIR,
            'sample_for_basic_types_no_default.json'
        )
        d = read_operation_json(f)

        # some INvalid user inputs corresponding to the input specifications
        sample_inputs = {
            'int_no_default_type': 10.5, 
            'positive_int_no_default_type': -3, 
            'nonnegative_int_no_default_type': -10, 
            'bounded_int_no_default_type': 22222,
            'float_no_default_type': 'abc', 
            'bounded_float_no_default_type': 10000.4, 
            'positive_float_no_default_type': -10.01, 
            'nonnegative_float_no_default_type': -0.1, 
            'string_no_default_type': '.*', 
            'boolean_no_default_type': 'abc'
        }

        # try to create objects for each- ensure they raise an exception:
        for key, val in sample_inputs.items():
            spec_object = d['inputs'][key]['spec']
            spec_type = spec_object['attribute_type']
            user_operation_input_class = user_operation_input_mapping[spec_type]
            with self.assertRaises(ValidationError):
                user_operation_input_class(self.regular_user_1, key, val, spec_object)

    def test_defaults_for_non_required_inputs(self):
        '''
        Certain inputs may not be required by the user. In that case, check that
        the defaults are properly entered as the value
        '''
        f = os.path.join(
            TESTDIR,
            'sample_for_basic_types.json'
        )
        d = read_operation_json(f)

        # try to create objects for each- ensure they raise an exception:
        for key, op_input in d['inputs'].items():
            spec_object = op_input['spec']
            spec_type = spec_object['attribute_type']
            user_operation_input_class = user_operation_input_mapping[spec_type]
            user_operation_input_class(self.regular_user_1, key, None, spec_object)

    def test_resource_type_input(self):
        '''
        Tests the various scenarios for handling an input corresponding to a 
        DataResource
        '''
        user_operation_input_class = user_operation_input_mapping['DataResource']

        user_resource_list = Resource.objects.filter(
            is_active=True,
            owner = self.regular_user_1
        )
        if len(user_resource_list) < 2:
            raise ImproperlyConfigured('Need at least two active user' 
                ' Resources for this test.'
            )

        other_user_resource = Resource.objects.create(
            is_active=True,
            owner = self.regular_user_2
        )

        # handle a good case with a single file
        r = user_resource_list[0]
        rt = r.resource_type
        single_resource_input_spec = {
            'attribute_type': 'DataResource',
            'many': False,
            'resource_types': [rt, ]
        }
        user_operation_input_class(self.regular_user_1,'xyz', 
            str(r.id), single_resource_input_spec)

        # handle a good case with multiple files
        r0 = user_resource_list[0]
        r1 = user_resource_list[1]
        typeset = set([r0.resource_type, r1.resource_type])
        multiple_resource_input_spec = {
            'attribute_type': 'DataResource',
            'many': True,
            'resource_types': list(typeset)
        }
        user_operation_input_class(self.regular_user_1,'xyz', 
            [str(r0.id), str(r1.id)], 
            multiple_resource_input_spec)

        # handle a single file with an invalid UUID; uuid is fine, but no Resource
        # handle a good case with a single file
        r = user_resource_list[0]
        rt = r.resource_type
        single_resource_input_spec = {
            'attribute_type': 'DataResource',
            'many': False,
            'resource_types': [rt, ]
        }
        with self.assertRaises(ValidationError):
            user_operation_input_class(self.regular_user_1,
                'xyz', str(uuid.uuid4()), single_resource_input_spec)

        # handle multiple files where one has an invalid UUID; uuid is fine, 
        # but no Resource
        multiple_resource_input_spec = {
            'attribute_type': 'DataResource',
            'many': True,
            'resource_types': []
        }
        with self.assertRaises(ValidationError):
            user_operation_input_class(self.regular_user_1,'xyz', 
                [str(uuid.uuid4()), str(uuid.uuid4())], 
                multiple_resource_input_spec)

        # handle the case where the UUID identifies a file, but it is not theirs
        rt = other_user_resource.resource_type
        single_resource_input_spec = {
            'attribute_type': 'DataResource',
            'many': False,
            'resource_types': [rt, ]
        }
        with self.assertRaises(ValidationError):
            user_operation_input_class(self.regular_user_1, 'xyz', 
                str(other_user_resource.id), single_resource_input_spec)

        # handle the case where the UUID identifies a file, but it is not the correct type
        r = user_resource_list[0]
        rt = r.resource_type
        other_resource_types = [x for x in RESOURCE_MAPPING.keys() if x != rt]
        single_resource_input_spec = {
            'attribute_type': 'DataResource',
            'many': False,
            'resource_types': other_resource_types
        }
        with self.assertRaises(ValidationError):
            user_operation_input_class(self.regular_user_1, 'xyz', 
                str(r.id), single_resource_input_spec)
