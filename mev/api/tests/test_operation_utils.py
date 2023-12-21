import unittest.mock as mock
import os
import json
import uuid

from django.core.exceptions import ImproperlyConfigured
from rest_framework.exceptions import ValidationError

from exceptions import ExecutedOperationInputOutputException, \
    InvalidResourceTypeException, \
    InactiveResourceException, \
    AttributeValueError

from data_structures.operation import Operation

from api.utilities.operations import read_operation_json, \
    validate_operation_inputs, \
    resource_operations_file_is_valid
from api.tests.base import BaseAPITestCase
from api.models import Operation as OperationDbModel
from api.models import Workspace, Resource

# the api/tests dir
TESTDIR = os.path.dirname(__file__)
TESTDIR = os.path.join(TESTDIR, 'operation_test_files')

class OperationUtilsTester(BaseAPITestCase):

    def setUp(self):
        self.filepath = os.path.join(TESTDIR, 'valid_workspace_operation.json')
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

    @mock.patch('api.utilities.operations.get_operation_instance')
    def test_user_input_validation(self, mock_get_operation_instance):
        '''
        Test that we receive back an appropriate object following
        successful validation. All the inputs below are valid
        '''
        f = os.path.join(
            TESTDIR,
            'sample_for_basic_types_no_default.json'
        )
        d = read_operation_json(f)
        op = Operation(d)
        mock_get_operation_instance.return_value = op

        # some valid user inputs corresponding to the input specifications
        sample_inputs = {
            'int_no_default_type': 10, 
            'positive_int_no_default_type': 3, 
            'nonnegative_int_no_default_type': 0, 
            'bounded_int_no_default_type': 2, 
            'float_no_default_type': 0.2, 
            'bounded_float_no_default_type': 0.4, 
            'positive_float_no_default_type': 0.01, 
            'nonnegative_float_no_default_type': 0.1, 
            'string_no_default_type': 'abc', 
            'boolean_no_default_type': True,
            'unrestrictedstring_no_default_type': 'A B',
            'option_string_no_default_type': 'xyz'
        }

        workspaces = Workspace.objects.all()
        if len(workspaces) == 0:
            raise ImproperlyConfigured('Need at least one Workspace to run this test.')
        final_inputs = validate_operation_inputs(self.regular_user_1, 
            sample_inputs, self.db_op, self.workspace)
        self.assertDictEqual(final_inputs, sample_inputs)

    @mock.patch('api.utilities.operations.get_operation_instance')
    def test_no_default_for_required_param(self, mock_get_operation_instance):
        '''
        Test that a missing required parameter triggers a validation error
        '''
        f = os.path.join(
            TESTDIR,
            'required_without_default.json'
        )
        d = read_operation_json(f)
        op = Operation(d)
        mock_get_operation_instance.return_value = op

        # one input was optional, one required. An empty payload
        # qualifies as a problem since it's missing the required key
        sample_inputs = {}

        with self.assertRaisesRegex(ValidationError, 'required_int_type'):
            validate_operation_inputs(self.regular_user_1, 
                sample_inputs, self.db_op, self.workspace)

    @mock.patch('api.utilities.operations.get_operation_instance')
    def test_optional_value_filled_by_default(self, mock_get_operation_instance):
        '''
        Test that a missing optional parameter gets the default value
        '''
        f = os.path.join(
            TESTDIR,
            'required_without_default.json'
        )
        d = read_operation_json(f)
        op = Operation(d)
        mock_get_operation_instance.return_value = op

        # one input was optional, one required.
        sample_inputs = {'required_int_type': 22}

        final_inputs = validate_operation_inputs(self.regular_user_1, 
            sample_inputs, self.db_op, self.workspace)
        self.assertEqual(final_inputs['required_int_type'], 22)
        expected_default = d['inputs']['optional_int_type']['spec']['default']
        self.assertEqual(
            final_inputs['optional_int_type'], expected_default)

    @mock.patch('api.utilities.operations.get_operation_instance')
    def test_optional_value_overridden(self, mock_get_operation_instance):
        '''
        Test that the optional parameter is overridden when given
        '''
        f = os.path.join(
            TESTDIR,
            'required_without_default.json'
        )
        d = read_operation_json(f)
        op = Operation(d)
        mock_get_operation_instance.return_value = op

        sample_inputs = {
            'required_int_type': 22,
            'optional_int_type': 33
        }

        final_inputs = validate_operation_inputs(self.regular_user_1, 
            sample_inputs, self.db_op, self.workspace)
        self.assertEqual(final_inputs['required_int_type'], 22)
        self.assertEqual(final_inputs['optional_int_type'], 33)

    @mock.patch('api.utilities.operations.get_operation_instance')
    def test_optional_without_default_becomes_none(self, mock_get_operation_instance):
        '''
        Generally, Operations with optional inputs should have defaults. However,
        if that is violated, the "input" should be assigned to be None
        '''
        f = os.path.join(
            TESTDIR,
            'optional_without_default.json'
        )
        d = read_operation_json(f)
        op = Operation(d)
        mock_get_operation_instance.return_value = op

        # the only input is optional, so this is technically fine.
        sample_inputs = {}

        #with self.assertRaises(ValidationError):
        final_inputs = validate_operation_inputs(self.regular_user_1, 
            sample_inputs, self.db_op, self.workspace)
        self.assertIsNone(final_inputs['optional_int_type'])

    @mock.patch('api.utilities.operations.get_operation_instance')
    def test_list_attr_inputs(self, mock_get_operation_instance):
        '''
        Test the case where inputs are of a list type (e.g. a list of strings)
        Check that it all validates as expected
        '''
        # first test one where we expect an empty list-- no resources
        # are used or created:
        f = os.path.join(
            TESTDIR,
            'valid_op_with_list_inputs.json'
        )
        d = read_operation_json(f)
        op = Operation(d)
        mock_get_operation_instance.return_value = op
        l1 = ['https://foo.com/bar', 'https://foo.com/baz']
        l2 = ['abc', 'def']
        inputs = {
            'link_list': l1,
            'regular_string_list': l2
        }
        ops = OperationDbModel.objects.all()
        op = ops[0]
        result = validate_operation_inputs(self.regular_user_1,
                inputs, op, None)
        self.assertIsNone(result['optional_input'])
        self.assertCountEqual(result['link_list'], l1)
        self.assertCountEqual(result['regular_string_list'], l2)

    @mock.patch('api.utilities.operations.get_operation_instance')
    @mock.patch('api.utilities.operations.check_resource_request_validity')
    def test_owned_resource_input(self, 
        mock_check_resource_request_validity, mock_get_operation_instance):
        '''
        Tests the cases where we have an input that is of type
        VaribleDataResource, which is owned. 
        
        In that case, we need to check that the passed
        input (a UUID) is a owned by the requesting user and associated
        with the workspace. Also test we raise an exceptionwhen those 
        checks fail
        '''
        f = os.path.join(
            TESTDIR,
            'valid_complete_workspace_operation.json'
        )
        d = read_operation_json(f)
        op = Operation(d)
        mock_get_operation_instance.return_value = op

        # test a case that works:
        all_r = Resource.objects.filter(owner=self.regular_user_1)
        r = all_r[0]
        r.resource_type = 'I_MTX'
        r.file_format = 'TSV'
        r.workspaces.add(self.workspace)
        r.save()

        mock_check_resource_request_validity.return_value = r
        sample_inputs = {
            'p_val': 0.05,
            'count_matrix': str(r.pk)
        }
        final_inputs = validate_operation_inputs(self.regular_user_1, 
            sample_inputs, self.db_op, self.workspace)
        self.assertDictEqual(final_inputs, sample_inputs)
     
        # test a case where the resource_type is invalid:
        r.resource_type = 'ACK'
        r.workspaces.add(self.workspace)
        r.save()
        mock_check_resource_request_validity.return_value = r
        with self.assertRaisesRegex(InvalidResourceTypeException, 'ACK'):
            final_inputs = validate_operation_inputs(self.regular_user_1, 
                sample_inputs, self.db_op, self.workspace)

        # test a case where the resource was not in the workspace
        r.resource_type = 'I_MTX'
        r.workspaces.set([])
        r.save()
        mock_check_resource_request_validity.return_value = r
        with self.assertRaisesRegex(
            ExecutedOperationInputOutputException, 
            'not part of the workspace'):
            final_inputs = validate_operation_inputs(self.regular_user_1, 
                sample_inputs, self.db_op, self.workspace)

        # test a case where there is an issue in the
        # `check_resource_request_validity` function
        # In this case, we mock that the resource was inactive
        mock_check_resource_request_validity.side_effect = \
            InactiveResourceException
        with self.assertRaises(InactiveResourceException):
            final_inputs = validate_operation_inputs(self.regular_user_1, 
                sample_inputs, self.db_op, self.workspace)

    @mock.patch('api.utilities.operations.get_operation_instance')
    @mock.patch('api.utilities.operations.check_resource_request_validity')
    def test_multiple_resource_input(self, 
        mock_check_resource_request_validity, mock_get_operation_instance):
        '''
        Tests the cases where we have an input that is of type
        VaribleDataResource with many=True, which permits a list
        of resource UUIDs 
        
        In that case, we need to check that each of the passed
        inputs (a UUID) is owned by the requesting user and associated
        with the workspace. Also test we raise an exception when those 
        checks fail
        '''
        f = os.path.join(
            TESTDIR,
            'valid_op_with_multiple_resource_input.json'
        )
        d = read_operation_json(f)
        op = Operation(d)
        mock_get_operation_instance.return_value = op

        # get two resources that are valid with the spec:
        all_r = Resource.objects.filter(owner=self.regular_user_1)
        r1 = all_r[0]
        r2 = all_r[1]
        r1.resource_type = 'I_MTX'
        r2.resource_type = 'EXP_MTX'
        r1.file_format = 'TSV'
        r2.file_format = 'TSV'
        r1.workspaces.add(self.workspace)
        r2.workspaces.add(self.workspace)
        r1.save()
        r2.save()
        mock_check_resource_request_validity.side_effect = [
            r1,
            r2
        ]
        sample_inputs = {
            'p_val': 0.05,
            'count_matrices': [str(r1.pk), str(r2.pk)]
        }
        final_inputs = validate_operation_inputs(self.regular_user_1, 
            sample_inputs, self.db_op, self.workspace)
        self.assertDictEqual(final_inputs, sample_inputs)
        mock_check_resource_request_validity.assert_has_calls([
            mock.call(self.regular_user_1, str(r1.pk)),
            mock.call(self.regular_user_1, str(r2.pk))
        ])

    @mock.patch('api.utilities.operations.get_operation_instance')
    @mock.patch('api.utilities.operations.check_resource_request_validity')
    def test_multiple_resource_input_with_bad_type(self, 
        mock_check_resource_request_validity, mock_get_operation_instance):
        '''
        Tests the cases where we have an input that is of type
        VaribleDataResource with many=True, which permits a list
        of resource UUIDs 
        
        Here, we take one of the resource types to be invalid-
        the spec says we only take certain types and somehow
        we receive a uuid referencing a resource with an
        invalid resource type
        '''
        f = os.path.join(
            TESTDIR,
            'valid_op_with_multiple_resource_input.json'
        )
        d = read_operation_json(f)
        op = Operation(d)
        mock_get_operation_instance.return_value = op

        # get two resources that are valid with the spec:
        all_r = Resource.objects.filter(owner=self.regular_user_1)
        r1 = all_r[0]
        r2 = all_r[1]
        r1.resource_type = 'FT'
        r2.resource_type = 'EXP_MTX'
        r1.file_format = 'TSV'
        r2.file_format = 'TSV'
        r1.workspaces.add(self.workspace)
        r2.workspaces.add(self.workspace)
        r1.save()
        r2.save()
        mock_check_resource_request_validity.side_effect = [
            r1,
            r2
        ]
        sample_inputs = {
            'p_val': 0.05,
            'count_matrices': [str(r1.pk), str(r2.pk)]
        }
        with self.assertRaisesRegex(InvalidResourceTypeException, 'FT'):
            validate_operation_inputs(self.regular_user_1, 
                sample_inputs, self.db_op, self.workspace)

        mock_check_resource_request_validity.assert_has_calls([
            mock.call(self.regular_user_1, str(r1.pk)),
            mock.call(self.regular_user_1, str(r2.pk))
        ])
     

    @mock.patch('api.utilities.operations.get_operation_instance')
    @mock.patch('api.utilities.operations.check_resource_request_validity')
    def test_optional_resource_input(self, 
        mock_check_resource_request_validity, mock_get_operation_instance):
        '''
        Tests the case where an input is a Resource, but it is not
        required. In that case, the supplied input is None
        '''
        f = os.path.join(
            TESTDIR,
            'optional_resource_input.json'
        )
        d = read_operation_json(f)
        op = Operation(d)
        mock_get_operation_instance.return_value = op

        sample_inputs = {
            'p_val': 0.05,
            'input_file': None
        }
        final_inputs = validate_operation_inputs(self.regular_user_1, 
            sample_inputs, self.db_op, self.workspace)
        self.assertDictEqual(final_inputs, sample_inputs)

    @mock.patch('api.utilities.operations.get_operation_instance')
    @mock.patch('api.utilities.operations.get_operation_resources_for_field')
    def test_resource_operation_inputs(self, 
        mock_get_operation_resources_for_field, mock_get_operation_instance):
        '''
        Tests the cases where we have an input that is of type
        OperationDataResource. In that case, we need to check that the passed
        input (a UUID) is an operation-associated resource for the 
        correct input field
        '''

        f = os.path.join(
            TESTDIR,
            'valid_op_with_operation_resource.json'
        )
        d = read_operation_json(f)
        op = Operation(d)
        mock_get_operation_instance.return_value = op

        # first test a case where this all works:
        pathway_file_uuid = uuid.uuid4()
        mock_db_op_resource1 = mock.MagicMock()
        mock_db_op_resource1.pk = pathway_file_uuid
        # the resource_type matches the type in the op file. 
        mock_db_op_resource1.resource_type = 'FT'     
        mock_db_op_resource2 = mock.MagicMock()
        mock_db_op_resource2.pk = str(uuid.uuid4())
        mock_get_operation_resources_for_field.return_value = [
            mock_db_op_resource2,
            mock_db_op_resource1
        ]
        sample_inputs = {
            'p_val': 0.05,
            'pathway_file': str(pathway_file_uuid)
        }
        final_inputs = validate_operation_inputs(self.regular_user_1, 
            sample_inputs, self.db_op, self.workspace)
        self.assertDictEqual(sample_inputs, final_inputs)

        # test the case where we get a matching resource op, but
        # *somehow* it has become corrupted and the resource_type
        # is no longer valid
        mock_db_op_resource1 = mock.MagicMock()
        mock_db_op_resource1.pk = pathway_file_uuid
        # the resource_type does NOT match the type in the op file. 
        mock_db_op_resource1.resource_type = 'ACK'     
        mock_get_operation_resources_for_field.return_value = [
            mock_db_op_resource2,
            mock_db_op_resource1
        ]
        with self.assertRaisesRegex(InvalidResourceTypeException, 'ACK'):
            final_inputs = validate_operation_inputs(self.regular_user_1, 
                sample_inputs, self.db_op, self.workspace)

        # Now test the case where a matching resource op is NOT found. 
        # First the case where OTHER resources are associated, but not
        # the one passed as an input
        mock_db_op_resource1 = mock.MagicMock()
        mock_db_op_resource1.pk = str(uuid.uuid4())   
        mock_db_op_resource2 = mock.MagicMock()
        mock_db_op_resource2.pk = str(uuid.uuid4())
        mock_get_operation_resources_for_field.return_value = [
            mock_db_op_resource2,
            mock_db_op_resource1
        ]
        sample_inputs = {
            'p_val': 0.05,
            'pathway_file': str(pathway_file_uuid)
        }
        with self.assertRaisesRegex(
            ExecutedOperationInputOutputException, 'not associated'):
            final_inputs = validate_operation_inputs(self.regular_user_1, 
                sample_inputs, self.db_op, self.workspace)
        
        # Now the case where no OperationResources are associated 
        mock_get_operation_resources_for_field.return_value = []
        with self.assertRaisesRegex(
            ExecutedOperationInputOutputException, 'not associated'):
            final_inputs = validate_operation_inputs(self.regular_user_1, 
                sample_inputs, self.db_op, self.workspace)

    def test_resource_operation_file_formatting(self):
        '''
        Test that we correctly parse resource operation specification files
        and reject those that do not conform to the spec.
        '''

        good_op_resource_data = {
            'inputA': [
                {
                    'name':'fileA',
                    'path':'/path/to/A.txt',
                    'resource_type':'MTX'
                },
                {
                    'name':'fileB',
                    'path':'/path/to/B.txt',
                    'resource_type':'MTX'
                }
            ]
        }
        inputs = {
            'inputA': '' # doesn't matter what the key points at. Only need the name
        }
        self.assertTrue(resource_operations_file_is_valid(good_op_resource_data, inputs.keys()))

        # change the inputs to have two necessary keys
        inputs = {
            'inputA': '',
            'inputB': ''
        }
        # should be false since we only have inputA in our "spec"
        self.assertFalse(resource_operations_file_is_valid(good_op_resource_data, inputs.keys()))

        bad_op_resource_data = {
            'inputA': [
                {
                    'name':'fileA',
                    'path':'/path/to/A.txt',
                    'resource_type':'MTX'
                },
                {
                    'name':'fileB',
                    'path':'/path/to/B.txt',
                    'resource_type':'MTX'
                }
            ],
            # should point at a list, but here points at a dict, which
            # could be a common formatting mistake
            'inputB': {
                'name':'fileC',
                'path':'/path/to/C.txt',
                'resource_type':'MTX'     
            }
        }

        # inputs to two necessary keys
        inputs = {
            'inputA': '',
            'inputB': ''
        }
        self.assertFalse(resource_operations_file_is_valid(bad_op_resource_data, inputs.keys()))

        good_op_resource_data = {
            'inputA': [
                {
                    'name':'fileA',
                    'path':'/path/to/A.txt',
                    'resource_type':'MTX'
                },
                {
                    'name':'fileB',
                    'path':'/path/to/B.txt',
                    'resource_type':'MTX'
                }
            ],
            'inputB': [
                {
                    'name':'fileC',
                    'path':'/path/to/C.txt',
                    'resource_type':'MTX'     
                }
            ]
        }

        # inputs to two necessary keys
        inputs = {
            'inputA': '',
            'inputB': ''
        }
        self.assertTrue(resource_operations_file_is_valid(good_op_resource_data, inputs.keys()))

        bad_op_resource_data = {
            'inputA': [
                {
                    'name':'fileA',
                    'path':'/path/to/A.txt',
                    'resource_type':'MTX'
                },
                {
                    'name':'fileB',
                    'path':'/path/to/A.txt', # path is the same as above. Not allowed.
                    'resource_type':'MTX'
                }
            ]
        }

        inputs = {
            'inputA': '',
        }
        self.assertFalse(resource_operations_file_is_valid(bad_op_resource_data, inputs.keys()))

        bad_op_resource_data = {
            'inputA': [
                {
                    'name':'fileA',
                    'path':'/path/to/A.txt',
                    'resource_type':'MTX'
                },
                {
                    'name':'fileA', # name matches above. Not allowed.
                    'path':'/path/to/B.txt',
                    'resource_type':'MTX'
                }
            ]
        }

        inputs = {
            'inputA': '',
        }
        self.assertFalse(resource_operations_file_is_valid(bad_op_resource_data, inputs.keys()))

        good_op_resource_data = {
            'inputA': [
                {
                    'name':'fileA',
                    'path':'/path/to/A.txt',
                    'resource_type':'MTX'
                },
                {
                    'name':'fileB',
                    'path':'/path/to/B.txt',
                    'resource_type':'MTX'
                }
            ],
            'inputB': [
                {
                    # the name/path match above, but since it's part of
                    # a different input, this is fine.
                    'name':'fileA',
                    'path':'/path/to/A.txt',
                    'resource_type':'MTX'     
                }
            ]
        }
        inputs = {
            'inputA': '',
            'inputB': ''
        }
        self.assertTrue(resource_operations_file_is_valid(good_op_resource_data, inputs.keys()))

        # one of the 'resources' is missing the resource_type key
        bad_op_resource_data = {
            'inputA': [
                {
                    'name':'fileA',
                    'path':'/path/to/A.txt',
                    'resource_type':'MTX'
                },
                {
                    'name':'fileA', # name matches above. Not allowed.
                    'path':'/path/to/B.txt'
                }
            ]
        }

        inputs = {
            'inputA': '',
        }
        self.assertFalse(resource_operations_file_is_valid(bad_op_resource_data, inputs.keys()))

    @mock.patch('api.utilities.operations.get_operation_instance')
    def test_optional_boolean_value_filled_by_default(self, mock_get_operation_instance):
        '''
        Test that a missing optional boolean parameter gets the default value
        '''
        f = os.path.join(
            TESTDIR,
            'valid_op_with_default_bool.json'
        )
        d = read_operation_json(f)
        op = Operation(d)
        mock_get_operation_instance.return_value = op

        # one input was optional, one required. An empty payload
        # qualifies as a problem since it's missing the required key
        sample_inputs = {}

        final_inputs = validate_operation_inputs(self.regular_user_1, 
            sample_inputs, self.db_op, self.workspace)
        self.assertEqual(final_inputs['some_boolean'], False)
        expected_default = d['inputs']['some_boolean']['spec']['default']
        self.assertEqual(
            final_inputs['some_boolean'], expected_default)

    @mock.patch('api.utilities.operations.get_operation_instance')
    def test_string_options_with_many(self, mock_get_operation_instance):
        '''
        Test the case where one of the inputs is an OptionString but 
        multiple inputs are permitted
        '''
        # first test one where we expect an empty list-- no resources
        # are used or created:
        f = os.path.join(
            TESTDIR,
            'valid_op_with_multiple_optionstring.json'
        )
        d = read_operation_json(f)
        op = Operation(d)
        mock_get_operation_instance.return_value = op
        l = ['abc', 'xyz']
        inputs = {
            'many_choices': l,
            'single_choice': 'abc'
        }
        ops = OperationDbModel.objects.all()
        op = ops[0]
        result = validate_operation_inputs(self.regular_user_1,
                inputs, op, None)
        self.assertCountEqual(result['many_choices'], l)
        self.assertCountEqual(result['single_choice'], 'abc')

        # you are allowed to pass a single choice even though
        # If many=True, you still need to pass inside a list
        l = ['abc']
        inputs = {
            'many_choices': l,
            'single_choice': 'abc'
        }
        ops = OperationDbModel.objects.all()
        op = ops[0]
        result = validate_operation_inputs(self.regular_user_1,
                inputs, op, None)
        self.assertCountEqual(result['many_choices'], l)
        self.assertCountEqual(result['single_choice'], 'abc')

        # make it fail by passing multiple choices to the second arg:
        inputs = {
            'many_choices': ['abc'],
            'single_choice': ['abc', 'xyz']
        }
        ops = OperationDbModel.objects.all()
        op = ops[0]
        with self.assertRaisesRegex(AttributeValueError, 'Multiple values'):
            result = validate_operation_inputs(self.regular_user_1,
                inputs, op, None)

        # make it fail by passing a string to the first arg:
        inputs = {
            'many_choices': 'abc',
            'single_choice': ['abc', 'xyz']
        }
        ops = OperationDbModel.objects.all()
        op = ops[0]
        with self.assertRaisesRegex(AttributeValueError, 'a list'):
            result = validate_operation_inputs(self.regular_user_1,
                inputs, op, None)