import unittest
import unittest.mock as mock
import os
import json
import copy
import uuid
import shutil
from collections import defaultdict

from django.core.exceptions import ImproperlyConfigured
from rest_framework.exceptions import ValidationError

from api.utilities.operations import read_operation_json
from api.data_structures.user_operation_input import user_operation_input_mapping
from api.models import Resource, Workspace, Operation, OperationResource
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
            'boolean_type': True, 
            'option_string_type': 'abc'
        }

        for key, val in sample_inputs.items():
            spec_object = d['inputs'][key]['spec']
            spec_type = spec_object['attribute_type']
            user_operation_input_class = user_operation_input_mapping[spec_type]
            user_operation_input_class(self.regular_user_1, None, None, key, val, spec_object)

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
            'boolean_no_default_type': 'abc',
            'option_string_no_default_type': 'zzz'
        }

        # try to create objects for each- ensure they raise an exception:
        for key, val in sample_inputs.items():
            spec_object = d['inputs'][key]['spec']
            spec_type = spec_object['attribute_type']
            user_operation_input_class = user_operation_input_mapping[spec_type]
            with self.assertRaises(ValidationError):
                # can pass None for the workspace arg since we don't use it when checking the basic types
                # Also pass None for the Operation argument. None of the basic attributes require that.
                user_operation_input_class(self.regular_user_1, None, None, key, val, spec_object)

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
            # can pass None for the workspace arg since we don't use it when checking the basic types
            user_operation_input_class(self.regular_user_1, None, None, key, None, spec_object)

    def test_resource_type_input(self):
        '''
        Tests the various scenarios for handling an input corresponding to a 
        DataResource
        '''
        user_operation_input_class = user_operation_input_mapping['DataResource']

        user_workspaces = Workspace.objects.filter(owner=self.regular_user_1) 

        has_valid_setup = False
        user_workspace = None
        for w in user_workspaces:
            workspace_resources = w.resources.all()
            user_resource_list = []
            for r in workspace_resources:
                if (r.is_active) and (r.owner == self.regular_user_1):
                    user_resource_list.append(r)
            if len(user_resource_list) >= 2:
                user_workspace = w
                has_valid_setup = True
                break
        if not has_valid_setup:
            raise ImproperlyConfigured('Need at least two active user' 
                ' Resources in a single Workspace for this test.'
            )

        # want to get another Resource owned by this user that is NOT in the workspace
        # They should NOT be able to execute an analysis on it unless it's associated with 
        # the workspace.
        non_workspace_resources = [x for x in 
            Resource.objects.filter(owner=self.regular_user_1) 
            if not x in user_resource_list]
        if len(non_workspace_resources) == 0:
            raise ImproperlyConfigured('Need at least one Resource for the user that is not'
                ' associated with a workspace.'
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
            'resource_type': rt
        }
        x = user_operation_input_class(self.regular_user_1, None, user_workspace,'xyz', 
            str(r.id), single_resource_input_spec)
        self.assertEqual(x.get_value(), str(r.id))

        # handle a good case with multiple files
        user_resource_dict = defaultdict(list)
        for r in user_resource_list:
            user_resource_dict[r.resource_type].append(r)

        rt = None
        for k,v in user_resource_dict.items():
            if len(v) > 1:
                rt = k
        if rt:
            r0 = user_resource_dict[rt][0]
            r1 = user_resource_dict[rt][1]
        else:
            raise ImproperlyConfigured('Set up the test such that there are '
                'multiple resources with the same type.'
            )
        multiple_resource_input_spec = {
            'attribute_type': 'DataResource',
            'many': True,
            'resource_type': rt
        }
        expected_vals = [str(r0.id), str(r1.id)]
        x = user_operation_input_class(self.regular_user_1, None, user_workspace,'xyz', 
            expected_vals, 
            multiple_resource_input_spec)
        self.assertCountEqual(x.get_value(), expected_vals)

        # malformatted input_spec (uses resource_typeS)
        r = user_resource_list[0]
        rt = r.resource_type
        single_resource_input_spec = {
            'attribute_type': 'DataResource',
            'many': False,
            'resource_types': rt
        }
        with self.assertRaises(ValidationError):
            user_operation_input_class(self.regular_user_1, None, user_workspace,
                'xyz', str(r.id), single_resource_input_spec)

        # malformatted input_spec (resource_type should be a str, not a list)
        r = user_resource_list[0]
        rt = r.resource_type
        single_resource_input_spec = {
            'attribute_type': 'DataResource',
            'many': False,
            'resource_type': [rt,]
        }
        with self.assertRaises(ValidationError):
            user_operation_input_class(self.regular_user_1, None, user_workspace,
                'xyz', str(r.id), single_resource_input_spec)

        # handle a single file with an invalid UUID; uuid is fine, but no Resource
        r = user_resource_list[0]
        rt = r.resource_type
        single_resource_input_spec = {
            'attribute_type': 'DataResource',
            'many': False,
            'resource_type': rt
        }
        with self.assertRaises(ValidationError):
            user_operation_input_class(self.regular_user_1, None, user_workspace,
                'xyz', str(uuid.uuid4()), single_resource_input_spec)

        # handle multiple files where one has an invalid UUID; uuid is fine, 
        # but no Resource
        multiple_resource_input_spec = {
            'attribute_type': 'DataResource',
            'many': True,
            'resource_type': 'MTX'
        }
        with self.assertRaises(ValidationError):
            user_operation_input_class(self.regular_user_1, None, user_workspace,'xyz', 
                [str(uuid.uuid4()), str(uuid.uuid4())], 
                multiple_resource_input_spec)

        # handle the case where the UUID identifies a file, but it is not theirs
        rt = other_user_resource.resource_type
        single_resource_input_spec = {
            'attribute_type': 'DataResource',
            'many': False,
            'resource_type': rt
        }
        with self.assertRaises(ValidationError):
            user_operation_input_class(self.regular_user_1, None, user_workspace, 'xyz', 
                str(other_user_resource.id), single_resource_input_spec)

        # handle the case where the UUID identifies a file, but it is not the correct type
        r = user_resource_list[0]
        rt = r.resource_type
        other_resource_types = [x for x in RESOURCE_MAPPING.keys() if x != rt]
        single_resource_input_spec = {
            'attribute_type': 'DataResource',
            'many': False,
            'resource_type': other_resource_types[0]
        }
        with self.assertRaises(ValidationError):
            user_operation_input_class(self.regular_user_1, None, user_workspace, 'xyz', 
                str(r.id), single_resource_input_spec)

        # handle the case where we have a list of UUIDs. They all identify
        # files, but for one of them, it is not the correct type
        r0 = user_resource_list[0]
        r1 = user_resource_list[1]
        rts = [r0.resource_type, r1.resource_type]
        other_resource_types = [x for x in RESOURCE_MAPPING.keys() if not x in rts]
        resource_input_spec = {
            'attribute_type': 'DataResource',
            'many': True,
            'resource_type': other_resource_types[0]
        }
        with self.assertRaises(ValidationError):
            user_operation_input_class(self.regular_user_1, None, user_workspace, 'xyz', 
                [str(r0.id), str(r1.id)], resource_input_spec)

        # handle the case where we have a list of UUIDs. They all identify
        # files, but one of them is not in the workspace (it is, however, owned
        # by the correct user.)
        r0 = user_resource_list[0]

        # get the resource_type for r0. Since we are dealing with an input
        # that expects a single type, we need to now get another, non-workspace
        # resource with that same type
        r1_found = False
        r1 = None
        idx = 0
        while ((not r1_found) and idx < len(non_workspace_resources)):
            if non_workspace_resources[idx].resource_type == r0.resource_type:
                r1_found = True
                r1 = non_workspace_resources[idx]
            idx += 1

        # just a double check
        rt_set = set([r0.resource_type, r1.resource_type])
        if len(rt_set) > 1:
            raise ImproperlyConfigured('Need two resources with the same type where'
                ' one is in the workspace and the other is not.'
            )
        resource_input_spec = {
            'attribute_type': 'DataResource',
            'many': True,
            'resource_type': list(rt_set)[0]
        }
        with self.assertRaises(ValidationError):
            user_operation_input_class(self.regular_user_1, None, user_workspace, 'xyz', 
                [str(r0.id), str(r1.id)], resource_input_spec)


    def test_variable_resource_type_input(self):
        '''
        Tests the various scenarios for handling an input corresponding to a 
        VariableDataResource
        '''
        user_operation_input_class = user_operation_input_mapping['VariableDataResource']

        user_workspaces = Workspace.objects.filter(owner=self.regular_user_1) 

        has_valid_setup = False
        user_workspace = None
        for w in user_workspaces:
            workspace_resources = w.resources.all()
            user_resource_list = []
            for r in workspace_resources:
                if (r.is_active) and (r.owner == self.regular_user_1):
                    user_resource_list.append(r)
            if len(user_resource_list) >= 2:
                user_workspace = w
                has_valid_setup = True
                break
        if not has_valid_setup:
            raise ImproperlyConfigured('Need at least two active user' 
                ' Resources in a single Workspace for this test.'
            )

        # want to get another Resource owned by this user that is NOT in the workspace
        # They should NOT be able to execute an analysis on it unless it's associated with 
        # the workspace.
        non_workspace_resources = [x for x in 
            Resource.objects.filter(owner=self.regular_user_1) 
            if not x in user_resource_list]
        if len(non_workspace_resources) == 0:
            raise ImproperlyConfigured('Need at least one Resource for the user that is not'
                ' associated with a workspace.'
            )

        other_user_resource = Resource.objects.create(
            is_active=True,
            owner = self.regular_user_2
        )

        # handle a good case with a single file
        r = user_resource_list[0]
        rt = r.resource_type
        single_resource_input_spec = {
            'attribute_type': 'VariableDataResource',
            'many': False,
            'resource_types': [rt,]
        }
        x = user_operation_input_class(self.regular_user_1, None, user_workspace,'xyz', 
            str(r.id), single_resource_input_spec)
        self.assertEqual(x.get_value(), str(r.id))

        # handle a good case with multiple files
        user_resource_dict = defaultdict(list)
        for r in user_resource_list:
            user_resource_dict[r.resource_type].append(r)

        rt = None
        for k,v in user_resource_dict.items():
            if len(v) > 1:
                rt = k
        if rt:
            r0 = user_resource_dict[rt][0]
            r1 = user_resource_dict[rt][1]
        else:
            raise ImproperlyConfigured('Set up the test such that there are '
                'multiple resources with the same type.'
            )
        multiple_resource_input_spec = {
            'attribute_type': 'VariableDataResource',
            'many': True,
            'resource_types': [rt,]
        }
        expected_vals = [str(r0.id), str(r1.id)]

        x = user_operation_input_class(self.regular_user_1, None, user_workspace,'xyz', 
            expected_vals, 
            multiple_resource_input_spec)
        self.assertCountEqual(x.get_value(), expected_vals)
        # malformatted input_spec (uses resource_type...singular)
        r = user_resource_list[0]
        rt = r.resource_type
        single_resource_input_spec = {
            'attribute_type': 'VariableDataResource',
            'many': False,
            'resource_type': [rt,]
        }
        with self.assertRaises(ValidationError):
            user_operation_input_class(self.regular_user_1, None, user_workspace,
                'xyz', str(r.id), single_resource_input_spec)

        # malformatted input_spec (resource_type should be a list, not a str)
        r = user_resource_list[0]
        rt = r.resource_type
        single_resource_input_spec = {
            'attribute_type': 'VariableDataResource',
            'many': False,
            'resource_types': rt
        }
        with self.assertRaises(ValidationError):
            user_operation_input_class(self.regular_user_1, None, user_workspace,
                'xyz', str(r.id), single_resource_input_spec)

        # handle a single file with an invalid UUID; uuid is fine, but no Resource
        r = user_resource_list[0]
        rt = r.resource_type
        single_resource_input_spec = {
            'attribute_type': 'VariableDataResource',
            'many': False,
            'resource_types': [rt,]
        }
        with self.assertRaises(ValidationError):
            user_operation_input_class(self.regular_user_1, None, user_workspace,
                'xyz', str(uuid.uuid4()), single_resource_input_spec)

        # handle multiple files where one has an invalid UUID; uuid is fine, 
        # but no Resource
        multiple_resource_input_spec = {
            'attribute_type': 'VariableDataResource',
            'many': True,
            'resource_types': ['MTX', 'I_MTX']
        }
        with self.assertRaises(ValidationError):
            user_operation_input_class(self.regular_user_1, None, user_workspace,'xyz', 
                [str(uuid.uuid4()), str(uuid.uuid4())], 
                multiple_resource_input_spec)

        # handle the case where the UUID identifies a file, but it is not theirs
        rt = other_user_resource.resource_type
        single_resource_input_spec = {
            'attribute_type': 'VariableDataResource',
            'many': False,
            'resource_types': [rt,]
        }
        with self.assertRaises(ValidationError):
            user_operation_input_class(self.regular_user_1, None, user_workspace, 'xyz', 
                str(other_user_resource.id), single_resource_input_spec)

        # handle the case where the UUID identifies a file, but it is not the correct type
        r = user_resource_list[0]
        rt = r.resource_type
        other_resource_types = [x for x in RESOURCE_MAPPING.keys() if x != rt]
        single_resource_input_spec = {
            'attribute_type': 'VariableDataResource',
            'many': False,
            'resource_types': other_resource_types
        }
        with self.assertRaises(ValidationError):
            user_operation_input_class(self.regular_user_1, None, user_workspace, 'xyz', 
                str(r.id), single_resource_input_spec)

        # handle the case where we have a list of UUIDs. They all identify
        # files, but for one of them, it is not the correct type
        r0 = user_resource_list[0]
        r1 = user_resource_list[1]
        rts = [r0.resource_type, r1.resource_type]
        other_resource_types = [x for x in RESOURCE_MAPPING.keys() if not x in rts]
        resource_input_spec = {
            'attribute_type': 'VariableDataResource',
            'many': True,
            'resource_types': other_resource_types
        }
        with self.assertRaises(ValidationError):
            user_operation_input_class(self.regular_user_1, None, user_workspace, 'xyz', 
                [str(r0.id), str(r1.id)], resource_input_spec)

        # handle the case where we have a list of UUIDs. They all identify
        # files, but one of them is not in the workspace (it is, however, owned
        # by the correct user.)
        r0 = user_resource_list[0]

        # get the resource_type for r0. Since we are dealing with an input
        # that expects a single type, we need to now get another, non-workspace
        # resource with that same type
        r1_found = False
        r1 = None
        idx = 0
        while ((not r1_found) and idx < len(non_workspace_resources)):
            if non_workspace_resources[idx].resource_type == r0.resource_type:
                r1_found = True
                r1 = non_workspace_resources[idx]
            idx += 1

        # just a double check
        rt_set = set([r0.resource_type, r1.resource_type])
        if len(rt_set) > 1:
            raise ImproperlyConfigured('Need two resources with the same type where'
                ' one is in the workspace and the other is not.'
            )
        resource_input_spec = {
            'attribute_type': 'VariableDataResource',
            'many': True,
            'resource_types': list(rt_set)
        }
        with self.assertRaises(ValidationError):
            user_operation_input_class(self.regular_user_1, None, user_workspace, 'xyz', 
                [str(r0.id), str(r1.id)], resource_input_spec)

    
    def test_operationresource_type_input(self):
        '''
        Tests the various scenarios for handling an input corresponding to a 
        OperationDataResource
        '''
        user_operation_input_class = user_operation_input_mapping['OperationDataResource']

        user_workspaces = Workspace.objects.filter(owner=self.regular_user_1) 
        user_workspace = user_workspaces[0]

        operations = Operation.objects.all()
        if len(operations) < 2:
            raise ImproperlyConfigured('Need at least two Operations to run this test.')
        op1 = operations[0]
        op2 = operations[1]

        # create an OperationDataResource for both ops
        r1 = OperationResource.objects.create(
            operation = op1,
            input_field = 'foo',
            name = 'foo.txt',
            resource_type = 'MTX'
        )
        r2 = OperationResource.objects.create(
            operation = op1,
            input_field = 'bar',
            name = 'bar.txt',
            resource_type = 'MTX'
        )
        r3 = OperationResource.objects.create(
            operation = op2,
            input_field = 'foo', # same input_field as above, but for a different op
            name = 'baz.txt',
            resource_type = 'MTX'
        )

        # handle a good case with a single file
        single_resource_input_spec = {
            'attribute_type': 'OperationDataResource',
            'many': False,
            'resource_type': r1.resource_type
        }
        x = user_operation_input_class(self.regular_user_1, op1, user_workspace, 'foo', 
            str(r1.id), single_resource_input_spec)
        self.assertEqual(x.get_value(), str(r1.id))

        # change the input field name. Note that r1 is associated with field 'foo', but
        # we mock a user trying to use that operationResource with a field named 'xyz'.
        # xyz is not a valid name for any input field.
        with self.assertRaises(ValidationError):
            user_operation_input_class(self.regular_user_1, op1, user_workspace, 'xyz', 
                str(r1.id), single_resource_input_spec)

        # change the input field name. Note that r1 is associated with field 'foo', but
        # we mock a user trying to use that operationResource with a field named 'bar'.
        # Here, 'bar' happens to be a valid name of a different input field
        with self.assertRaises(ValidationError):
            user_operation_input_class(self.regular_user_1, op1, user_workspace, 'bar', 
                str(r1.id), single_resource_input_spec)

        # assert that this is valid
        x = user_operation_input_class(self.regular_user_1, op1, user_workspace, 'bar', 
            str(r2.id), single_resource_input_spec)
        self.assertEqual(x.get_value(), str(r2.id))

        # op2 has a 'foo' input field- check that it works before trying to create a 
        # failed example
        x = user_operation_input_class(self.regular_user_1, op2, user_workspace, 'foo', 
            str(r3.id), single_resource_input_spec)
        self.assertEqual(x.get_value(), str(r3.id))
        # now change the user input to be the UUID of r1. This resource has the same
        # input field, but is assoc. with op1, not op2
        with self.assertRaises(ValidationError):
            user_operation_input_class(self.regular_user_1, op2, user_workspace, 'foo', 
                str(r1.id), single_resource_input_spec)

        # change the resource_type for the input spec so 
        # it doesn't match the OperationResource. 
        single_resource_input_spec = {
            'attribute_type': 'OperationDataResource',
            'many': False,
            'resource_type': 'XYZ'
        }
        with self.assertRaises(ValidationError):
            user_operation_input_class(self.regular_user_1, op1, user_workspace, 'foo', 
                str(r1.id), single_resource_input_spec)

        # change the resource_type for the input spec so 
        # it doesn't match the format. It should be a string
        # but it's a list
        single_resource_input_spec = {
            'attribute_type': 'OperationDataResource',
            'many': False,
            'resource_type': [r1.resource_type,]
        }
        with self.assertRaises(ValidationError):
            user_operation_input_class(self.regular_user_1, op1, user_workspace, 'foo', 
                str(r1.id), single_resource_input_spec)

    def test_observation_set_inputs(self):
        '''
        Tests that the inputs are properly validated when they
        correspond to an input type of `ObservationSet`
        '''
        f = os.path.join(
            TESTDIR,
            'obs_set_test.json'
        )
        d = read_operation_json(f)

        clazz = user_operation_input_mapping['ObservationSet']

        valid_obs_1 = {
            'id': 'foo',
            'attributes': {
                'treatment': {'attribute_type': 'String', 'value': 'A'}
            }
        }
        valid_obs_2 = {
            'id': 'bar',
            'attributes': {
                'treatment': {'attribute_type': 'String', 'value': 'B'}
            }
        }

        valid_obs_set = {
            'multiple': True,
            'elements': [
                valid_obs_1,
                valid_obs_2
            ]
        }

        # test that we are fine with a valid input:
        x=clazz(self.regular_user_1, None, None, 'xyz', valid_obs_set, d['inputs']['obs_set_type'])
        val = x.get_value()
        self.assertEqual(val['multiple'], valid_obs_set['multiple'])
        self.assertCountEqual(val['elements'], valid_obs_set['elements'])

        invalid_obs_set = {
            'multiple': False,
            'elements': [
                valid_obs_1,
                valid_obs_2
            ]
        }
        # the >1 elements coupled with multiple=False makes this an invalid ObservationSet
        with self.assertRaises(ValidationError):
            clazz(self.regular_user_1, None, None, 'xyz', invalid_obs_set, d['inputs']['obs_set_type'])

        valid_obs_set = {
            'multiple': True,
            'elements': [
                valid_obs_1,
                {'id': 'baz'} # missing the 'attributes' key, but that is OK
            ]
        }
        clazz(self.regular_user_1, None, None, 'xyz', valid_obs_set, d['inputs']['obs_set_type'])

        invalid_obs_set = {
            'multiple': True,
            'elements': [
                valid_obs_1,
                {} # missing the 'id' key, which is required
            ]
        }
        # missing 'id' causes the nested Observation to be invalid
        with self.assertRaises(ValidationError):
            clazz(self.regular_user_1, None, None, 'xyz', invalid_obs_set, d['inputs']['obs_set_type'])

    def test_feature_set_inputs(self):
        '''
        Tests that the inputs are properly validated when they
        correspond to an input type of `FeatureSet`
        '''
        f = os.path.join(
            TESTDIR,
            'feature_set_test.json'
        )
        d = read_operation_json(f)

        clazz = user_operation_input_mapping['FeatureSet']

        valid_feature_1 = {
            'id': 'foo',
            'attributes': {}
        }
        valid_feature_2 = {
            'id': 'bar',
            'attributes': {}
        }

        valid_feature_set = {
            'multiple': True,
            'elements': [
                valid_feature_1,
                valid_feature_2
            ]
        }

        # test that we are fine with a valid input:
        x = clazz(self.regular_user_1, None, None, 'xyz', valid_feature_set, d['inputs']['feature_set_type'])
        val = x.get_value()
        self.assertEqual(val['multiple'], valid_feature_set['multiple'])
        self.assertCountEqual(val['elements'], valid_feature_set['elements'])

        invalid_feature_set = {
            'multiple': False,
            'elements': [
                valid_feature_1,
                valid_feature_2
            ]
        }
        # the >1 elements coupled with multiple=False makes this an invalid FeatureSet
        with self.assertRaises(ValidationError):
            clazz(self.regular_user_1, None, None, 'xyz', invalid_feature_set, d['inputs']['feature_set_type'])

        valid_feature_set2 = {
            'multiple': True,
            'elements': [
                valid_feature_1,
                {'id': 'bar'} # missing the 'attributes' key, but that is OK
            ]
        }
        x = clazz(self.regular_user_1, None, None, 'xyz', valid_feature_set2, d['inputs']['feature_set_type'])
        # note that we compare against the original valid_feature_set.
        # This is because our methods add the empty 'attributes' key.
        # Therefore, a strict comparison of valid_feature_set2 would not be possible
        # as we designed THAT dict to be missing the 'attributes' key.
        val = x.get_value()
        self.assertEqual(val['multiple'], valid_feature_set['multiple'])
        self.assertCountEqual(val['elements'], valid_feature_set['elements'])

        invalid_feature_set = {
            'multiple': True,
            'elements': [
                valid_feature_1,
                {} # missing the 'id' key, which is required
            ]
        }
        # missing 'id' causes the nested Feature to be invalid
        with self.assertRaises(ValidationError):
            clazz(self.regular_user_1, None, None, 'xyz', invalid_feature_set, d['inputs']['feature_set_type'])

    def test_observation_inputs(self):
        '''
        Tests that the inputs are properly validated when they
        correspond to an input type of `Observation`
        '''
        f = os.path.join(
            TESTDIR,
            'obs_set_test.json'
        )
        d = read_operation_json(f)

        clazz = user_operation_input_mapping['Observation']

        valid_obs_1 = {
            'id': 'foo',
            'attributes': {
                'treatment': {'attribute_type': 'String', 'value': 'A'}
            }
        }
        valid_obs_2 = {
            'id': 'foo'
        }
        invalid_obs = {
            'attributes': {
                'treatment': {'attribute_type': 'String', 'value': 'A'}
            }
        }

        # test that we are fine with a valid input:
        x = clazz(self.regular_user_1, None, None, 'xyz', valid_obs_1, d['inputs']['obs_type'])
        y = clazz(self.regular_user_1, None, None, 'xyz', valid_obs_2, d['inputs']['obs_type'])
        self.assertDictEqual(x.get_value(), valid_obs_1)
        self.assertDictEqual(
            y.get_value(), 
            {'id': 'foo', 'attributes':{} }
        )


        with self.assertRaises(ValidationError):
            clazz(self.regular_user_1, None, None, 'xyz', invalid_obs, d['inputs']['obs_type'])

    def test_feature_inputs(self):
        '''
        Tests that the inputs are properly validated when they
        correspond to an input type of `Feature`
        '''
        f = os.path.join(
            TESTDIR,
            'feature_set_test.json'
        )
        d = read_operation_json(f)

        clazz = user_operation_input_mapping['Feature']

        valid_feature_1 = {
            'id': 'foo',
            'attributes': {
                'treatment': {'attribute_type':'String','value':'A'}
            }
        }
        valid_feature_2 = {
            'id': 'foo'
        }
        invalid_feature = {
            'attributes': {
                'treatment': 'A'
            }
        }

        # test that we are fine with a valid input:
        x = clazz(self.regular_user_1, None, None, 'xyz', valid_feature_1, d['inputs']['feature_type'])
        y = clazz(self.regular_user_1, None, None, 'xyz', valid_feature_2, d['inputs']['feature_type'])
        self.assertDictEqual(x.get_value(), valid_feature_1)
        self.assertDictEqual(
            y.get_value(), 
            {'id': 'foo', 'attributes':{} }
        )
        with self.assertRaises(ValidationError):
            clazz(self.regular_user_1, None, None, 'xyz', invalid_feature, d['inputs']['feature_type'])