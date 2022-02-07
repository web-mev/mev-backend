import unittest
import unittest.mock as mock
import os
import json
import uuid

from django.core.exceptions import ImproperlyConfigured
from rest_framework.exceptions import ValidationError

from api.tests.base import BaseAPITestCase
from api.models import Workspace, \
    Resource, \
    ExecutedOperation, \
    WorkspaceExecutedOperation, \
    Operation
from api.converters.output_converters import LocalDockerOutputConverter
from api.exceptions import OutputConversionException

# the api/tests dir
TESTDIR = os.path.dirname(__file__)
TESTDIR = os.path.join(TESTDIR, 'operation_test_files')

class ExecutedOperationOutputConverterTester(BaseAPITestCase):

    def setUp(self):
        self.establish_clients()

    def test_basic_attribute_outputs(self):

        all_user_workspaces = Workspace.objects.filter(owner=self.regular_user_1)
        if len(all_user_workspaces) < 1:
            raise ImproperlyConfigured('Need at least one Workspace for the regular user.')
        workspace = all_user_workspaces[0]

        c = LocalDockerOutputConverter()
        job_id = str(uuid.uuid4())
        op = Operation.objects.all()[0]
        job_name = 'foo'
        executed_op = WorkspaceExecutedOperation.objects.create(
            id=job_id,
            workspace=workspace,
            owner=self.regular_user_1,
            inputs = {},
            operation = op,
            mode = '',
            job_name = job_name
        )

        j = json.load(open(os.path.join(TESTDIR, 'non_resource_outputs.json')))
        output_spec = j['outputs']['pval']['spec']
        return_val = c.convert_output(executed_op, workspace, output_spec, 0.2)
        self.assertEqual(return_val, 0.2)

        with self.assertRaises(OutputConversionException) as ex:
            return_val = c.convert_output(executed_op, workspace, output_spec, -0.2)

        output_spec = j['outputs']['some_integer']['spec']
        with self.assertRaises(OutputConversionException) as ex:
            return_val = c.convert_output(executed_op, workspace, output_spec, 0.2)

        # we are strict and don't accept string-cast integers. 
        output_spec = j['outputs']['some_integer']['spec']
        with self.assertRaises(OutputConversionException) as ex:
            return_val = c.convert_output(executed_op, workspace, output_spec, '1')


        output_spec = j['outputs']['some_bool']['spec']
        self.assertTrue(c.convert_output(executed_op, workspace, output_spec, True))
        with self.assertRaises(OutputConversionException) as ex:
            return_val = c.convert_output(executed_op, workspace, output_spec, '1')

class DataResourceOutputConverterTester(BaseAPITestCase):

    def setUp(self):
        self.establish_clients()

    @mock.patch('api.converters.output_converters.validate_and_store_resource')
    @mock.patch('api.converters.output_converters.ResourceMetadata')
    @mock.patch('api.converters.output_converters.BaseOutputConverter.create_resource')
    def test_dataresource_converts_properly(self,
        mock_create_resource, 
        mock_resourcemetadata_model, 
        mock_validate_and_store_resource):
        '''
        When a DataResource is created as part of an ExecutedOperation,
        the outputs give it as a path (or list of paths). Here we test the single value

        The converter's job is to register that as a new file with the workspace
        and return the UUID of this new Resource
        '''

        resource_type = 'MTX'
        resource_uuid = uuid.uuid4()

        mock_resource = mock.MagicMock()
        mock_resource.resource_type = resource_type
        mock_resource.pk = resource_uuid
        mock_create_resource.return_value = mock_resource

        mock_resource_metadata_obj = mock.MagicMock()
        mock_resourcemetadata_model.objects.get.return_value = mock_resource_metadata_obj

        all_user_workspaces = Workspace.objects.filter(owner=self.regular_user_1)
        if len(all_user_workspaces) < 1:
            raise ImproperlyConfigured('Need at least one Workspace for the regular user.')
        workspace = all_user_workspaces[0]

        c = LocalDockerOutputConverter()
        job_id = str(uuid.uuid4())
        op = Operation.objects.all()[0]
        job_name = 'foo'
        executed_op = WorkspaceExecutedOperation.objects.create(
            id=job_id,
            workspace=workspace,
            owner=self.regular_user_1,
            inputs = {},
            operation = op,
            mode = '',
            job_name = job_name
        )
        output_spec = {
            'attribute_type': 'DataResource',
            'many': False,
            'resource_type': resource_type
        }
        mock_path = '/some/output/path.txt'
        expected_name = '{n}.path.txt'.format(n=job_name)
        return_val = c.convert_output(executed_op, workspace, output_spec, mock_path)

        mock_create_resource.assert_called_with(
            self.regular_user_1,
            workspace,
            mock_path,
            expected_name
        )
        mock_validate_and_store_resource.assert_called()
        mock_resourcemetadata_model.objects.get.assert_called()
        mock_resource_metadata_obj.save.assert_called()
        self.assertEqual(return_val, str(resource_uuid))


    @mock.patch('api.converters.output_converters.validate_and_store_resource')
    @mock.patch('api.converters.output_converters.ResourceMetadata')
    @mock.patch('api.converters.output_converters.BaseOutputConverter.create_resource')
    def test_dataresource_converts_list_properly(self,
        mock_create_resource, 
        mock_resourcemetadata_model, 
        mock_validate_and_store_resource):
        '''
        When a DataResource is created as part of an ExecutedOperation,
        the outputs give it as a path (or list of paths). Here we test the list of paths

        The converter's job is to register that as a new file with the workspace
        and return the UUID of this new Resources
        '''

        resource_type = 'MTX'
        resource1_uuid = uuid.uuid4()
        resource2_uuid = uuid.uuid4()

        mock_resource1 = mock.MagicMock()
        mock_resource2 = mock.MagicMock()
        mock_resource1.resource_type = resource_type
        mock_resource2.resource_type = resource_type
        mock_resource1.pk = resource1_uuid
        mock_resource2.pk = resource2_uuid
        mock_create_resource.side_effect = [mock_resource1, mock_resource2]

        mock_resource_metadata_obj1 = mock.MagicMock()
        mock_resource_metadata_obj2 = mock.MagicMock()
        mock_resourcemetadata_model.objects.get.side_effect = [
            mock_resource_metadata_obj1,
            mock_resource_metadata_obj2
        ]

        all_user_workspaces = Workspace.objects.filter(owner=self.regular_user_1)
        if len(all_user_workspaces) < 1:
            raise ImproperlyConfigured('Need at least one Workspace for the regular user.')
        workspace = all_user_workspaces[0]

        c = LocalDockerOutputConverter()
        job_id = str(uuid.uuid4())
        op = Operation.objects.all()[0]
        job_name = 'foo'
        executed_op = WorkspaceExecutedOperation.objects.create(
            id=job_id,
            workspace=workspace,
            owner=self.regular_user_1,
            inputs = {},
            operation = op,
            mode = '',
            job_name = job_name
        )
        output_spec = {
            'attribute_type': 'DataResource',
            'many': True,
            'resource_type': resource_type
        }
        mock_path1 = '/some/output/path1.txt'
        mock_path2 = '/some/output/path2.txt'
        return_val = c.convert_output(executed_op, 
            workspace, 
            output_spec, 
            [
                mock_path1,
                mock_path2
            ]
        )

        expected_name1 = '{n}.path1.txt'.format(n=job_name)
        expected_name2 = '{n}.path2.txt'.format(n=job_name)
        call1 = mock.call(
            self.regular_user_1,
            workspace,
            mock_path1,
            expected_name1
        )
        call2 = mock.call(
            self.regular_user_1,
            workspace,
            mock_path2,
            expected_name2
        )
        mock_create_resource.assert_has_calls([
            call1,
            call2
        ])
        self.assertEqual(mock_validate_and_store_resource.call_count, 2)
        self.assertEqual(mock_resourcemetadata_model.objects.get.call_count, 2)
        mock_resource_metadata_obj1.save.assert_called()
        mock_resource_metadata_obj2.save.assert_called()
        self.assertCountEqual(return_val, [str(resource1_uuid), str(resource2_uuid)])

    @mock.patch('api.converters.output_converters.validate_and_store_resource')
    @mock.patch('api.converters.output_converters.ResourceMetadata')
    @mock.patch('api.converters.output_converters.BaseOutputConverter.create_resource')
    @mock.patch('api.converters.output_converters.delete_resource_by_pk')
    def test_dataresource_failure_handled_properly(self,
        mock_delete_resource_by_pk,
        mock_create_resource, 
        mock_resourcemetadata_model, 
        mock_validate_and_store_resource):
        '''
        Here we test that the proper functions are called when one of the outputs
        fails validation.

        The first one "passes validation", but the second one will fail.
        '''

        resource_type = 'MTX'
        resource1_uuid = uuid.uuid4()
        resource2_uuid = uuid.uuid4()

        mock_resource1 = mock.MagicMock()
        mock_resource2 = mock.MagicMock()
        mock_resource1.resource_type = resource_type
        # don't set the resource_type on mock_resource2 so it 
        # mocks the validation failure.

        mock_resource1.pk = resource1_uuid
        mock_resource2.pk = resource2_uuid
        mock_create_resource.side_effect = [mock_resource1, mock_resource2]

        mock_resource_metadata_obj1 = mock.MagicMock()
        mock_resourcemetadata_model.objects.get.return_value = mock_resource_metadata_obj1

        all_user_workspaces = Workspace.objects.filter(owner=self.regular_user_1)
        if len(all_user_workspaces) < 1:
            raise ImproperlyConfigured('Need at least one Workspace for the regular user.')
        workspace = all_user_workspaces[0]

        c = LocalDockerOutputConverter()
        job_id = str(uuid.uuid4())
        op = Operation.objects.all()[0]
        job_name = 'foo'
        executed_op = WorkspaceExecutedOperation.objects.create(
            id=job_id,
            workspace=workspace,
            owner=self.regular_user_1,
            inputs = {},
            operation = op,
            mode = '',
            job_name = job_name
        )
        output_spec = {
            'attribute_type': 'DataResource',
            'many': True,
            'resource_type': resource_type
        }
        mock_path1 = '/some/output/path1.txt'
        mock_path2 = '/some/output/path2.txt'
        with self.assertRaises(OutputConversionException) as ex:
            c.convert_output(executed_op, 
                workspace, 
                output_spec, 
                [
                    mock_path1,
                    mock_path2
                ]
            )

        # the create_resource method should have been called twice
        expected_name1 = '{n}.path1.txt'.format(n=job_name)
        expected_name2 = '{n}.path2.txt'.format(n=job_name)
        call1 = mock.call(
            self.regular_user_1,
            workspace,
            mock_path1,
            expected_name1
        )
        call2 = mock.call(
            self.regular_user_1,
            workspace,
            mock_path2,
            expected_name2
        )
        mock_create_resource.assert_has_calls([
            call1,
            call2
        ])
        
        self.assertEqual(mock_resourcemetadata_model.objects.get.call_count, 1)
        mock_resource_metadata_obj1.save.assert_called()

        mock_delete_resource_by_pk.assert_has_calls([
            mock.call(str(resource1_uuid)),
            mock.call(str(resource2_uuid))
        ], any_order = True)

    @mock.patch('api.converters.output_converters.validate_and_store_resource')
    @mock.patch('api.converters.output_converters.ResourceMetadata')
    @mock.patch('api.converters.output_converters.BaseOutputConverter.create_resource')
    def test_dataresource_converts_properly_case2(self, 
        mock_create_resource,
        mock_resourcemetadata_model, 
        mock_validate_and_store_resource):
        '''
        When a DataResource is created as part of an ExecutedOperation,
        the outputs give it as a path (or list of paths)

        The converter's job is to register that as a new file with the workspace
        and return the UUID of this new Resource

        Here, we have a non-workspace Op, so we check that we only create a Resource
        but do not associate it with any Workspaces
        '''

        resource_type = 'MTX'
        resource_uuid = uuid.uuid4()

        mock_resource = mock.MagicMock()
        mock_resource.resource_type = resource_type
        mock_resource.pk = resource_uuid
        mock_create_resource.return_value = mock_resource

        mock_resource_metadata_obj = mock.MagicMock()
        mock_resourcemetadata_model.objects.get.return_value = mock_resource_metadata_obj

        c = LocalDockerOutputConverter()
        job_id = str(uuid.uuid4())
        op = Operation.objects.all()[0]
        op.workspace_operation = False
        op.save()
        executed_op = ExecutedOperation.objects.create(
            id=job_id,
            owner=self.regular_user_1,
            inputs = {},
            operation = op,
            mode = ''
        )
        output_spec = {
            'attribute_type': 'DataResource',
            'many': False,
            'resource_type': resource_type
        }

        mock_path = '/some/output/path.txt'
        expected_name = 'path.txt'
        return_val = c.convert_output(executed_op, None, output_spec, mock_path)

        mock_create_resource.assert_called_with(
            self.regular_user_1,
            None,
            mock_path,
            expected_name
        )
        mock_validate_and_store_resource.assert_called()
        mock_resourcemetadata_model.objects.get.assert_called()
        mock_resource_metadata_obj.save.assert_called()
        self.assertEqual(return_val, str(resource_uuid))


class VariableDataResourceOutputConverterTester(BaseAPITestCase):

    def setUp(self):
        self.establish_clients()

    @mock.patch('api.converters.output_converters.validate_and_store_resource')
    @mock.patch('api.converters.output_converters.ResourceMetadata')
    @mock.patch('api.converters.output_converters.BaseOutputConverter.create_resource')
    def test_variabledataresource_conversion_failures_handled_properly(self,
        mock_create_resource, 
        mock_resourcemetadata_model, 
        mock_validate_and_store_resource):
        '''
        When a VariableDataResource is created as part of an ExecutedOperation,
        the outputs give it as an object with keys of `path` and `resource_type`. 
        Recall that VariableDataResource instances allow us to dynamically set the 
        resource type of the output files.

        The converter's job is to register that as a new file with the workspace
        and return the UUID of this new Resource

        Here, we test the various ways this conversion can fail due to improperly formatted
        "payloads" produced by the ExecutedOperation. Failures there are limited to those
        introduced by analysis tool developers (e.g. they did not produce a correctly 
        formatted outputs.json as part of the analysis)
        '''

        all_user_workspaces = Workspace.objects.filter(owner=self.regular_user_1)
        if len(all_user_workspaces) < 1:
            raise ImproperlyConfigured('Need at least one Workspace for the regular user.')
        workspace = all_user_workspaces[0]

        c = LocalDockerOutputConverter()
        job_id = str(uuid.uuid4())
        op = Operation.objects.all()[0]
        job_name = 'foo'
        executed_op = WorkspaceExecutedOperation.objects.create(
            id=job_id,
            workspace=workspace,
            owner=self.regular_user_1,
            inputs = {},
            operation = op,
            mode = '',
            job_name = job_name
        )
        output_spec = {
            'attribute_type': 'VariableDataResource',
            'many': False,
            'resource_types': ['MTX', 'I_MTX']
        }

        # try with a string- should raise an exception since the resource type is not known
        # otherwise
        with self.assertRaisesRegex(OutputConversionException, 'provided as an object/dict'):
            c.convert_output(executed_op, workspace, output_spec, '/some/output/path.txt')
        mock_create_resource.assert_not_called()

        # try with a dict, but one that does not have the correct keys 
        # (missing the resource_type key)
        with self.assertRaisesRegex(OutputConversionException, 'resource_type') as ex:
            c.convert_output(executed_op, workspace, output_spec, 
                {
                    'path':'/some/output/path.txt',
                }
            )
        mock_create_resource.assert_not_called()

        # try with a dict, but one that does not have the correct keys 
        # (missing the path key)
        with self.assertRaisesRegex(OutputConversionException, 'path') as ex:
            c.convert_output(executed_op, workspace, output_spec, 
                {
                    'pathS':'/some/output/path.txt',
                    'resource_type': 'MTX'
                }
            )
        mock_create_resource.assert_not_called()

        # a resource_type that doesn't match the spec
        with self.assertRaisesRegex(OutputConversionException, 'ANN'):
            c.convert_output(executed_op, workspace, output_spec, 
                {
                    'path':'/some/output/path.txt',
                    'resource_type': 'ANN'
                }
            )
        mock_create_resource.assert_not_called()

        # the output is a list (with many =False set above)
        with self.assertRaisesRegex(OutputConversionException, 'dict'):
            c.convert_output(executed_op, workspace, output_spec, 
                [{
                    'path':'/some/output/path.txt',
                    'resource_type': 'MTX'
                },]
            )
        mock_create_resource.assert_not_called()

        # change the output spec so that we accept multiple outputs (many=True)
        output_spec = {
            'attribute_type': 'VariableDataResource',
            'many': True,
            'resource_types': ['MTX', 'I_MTX']
        }

        # since many=True, then we should be passing a list of objects. Here,
        # we only pass a single object.
        with self.assertRaisesRegex(OutputConversionException, 'expect a list') as ex:
            c.convert_output(executed_op, workspace, output_spec, 
                {
                    'path':'/some/output/path.txt',
                    'resource_type': 'ANN'
                }
            )
        mock_create_resource.assert_not_called()

        # here, the first and only item has the wrong type
        with self.assertRaisesRegex(OutputConversionException, 'ANN') as ex:
            c.convert_output(executed_op, workspace, output_spec, 
                [{
                    'path':'/some/output/path.txt',
                    'resource_type': 'ANN'
                }]
            )
        mock_create_resource.assert_not_called()

    @mock.patch('api.converters.output_converters.validate_and_store_resource')
    @mock.patch('api.converters.output_converters.ResourceMetadata')
    @mock.patch('api.converters.output_converters.BaseOutputConverter.create_resource')
    def test_variabledataresource_conversion_handled_properly(self,
        mock_create_resource, 
        mock_resourcemetadata_model, 
        mock_validate_and_store_resource):
        '''
        When a VariableDataResource is created as part of an ExecutedOperation,
        the outputs give it as an object with keys of `path` and `resource_type`. 
        Recall that VariableDataResource instances allow us to dynamically set the 
        resource type of the output files.

        The converter's job is to register that as a new file with the workspace
        and return the UUID of this new Resource
        '''
        resource_type = 'MTX'
        resource_uuid = uuid.uuid4()

        mock_resource = mock.MagicMock()
        mock_resource.resource_type = resource_type
        mock_resource.pk = resource_uuid
        mock_create_resource.return_value = mock_resource

        mock_resource_metadata_obj = mock.MagicMock()
        mock_resourcemetadata_model.objects.get.return_value = mock_resource_metadata_obj

        all_user_workspaces = Workspace.objects.filter(owner=self.regular_user_1)
        if len(all_user_workspaces) < 1:
            raise ImproperlyConfigured('Need at least one Workspace for the regular user.')
        workspace = all_user_workspaces[0]

        c = LocalDockerOutputConverter()
        job_id = str(uuid.uuid4())
        op = Operation.objects.all()[0]
        job_name = 'foo'
        executed_op = WorkspaceExecutedOperation.objects.create(
            id=job_id,
            workspace=workspace,
            owner=self.regular_user_1,
            inputs = {},
            operation = op,
            mode = '',
            job_name = job_name
        )
        output_spec = {
            'attribute_type': 'VariableDataResource',
            'many': False,
            'resource_types': ['MTX', 'I_MTX']
        }
        # a good request- has the proper format for the output and the resource_type is 
        # permitted (based on the output_spec)
        mock_path = '/some/output/path.txt'
        return_val = c.convert_output(executed_op, workspace, output_spec, 
            {
                'path': mock_path,
                'resource_type': resource_type
            }
        )
        expected_name = '{n}.path.txt'.format(n=job_name)
        mock_create_resource.assert_called_with(
            self.regular_user_1,
            workspace,
            mock_path,
            expected_name   
        )
        mock_validate_and_store_resource.assert_called()
        mock_resourcemetadata_model.objects.get.assert_called()
        mock_resource_metadata_obj.save.assert_called()
        self.assertEqual(return_val, str(resource_uuid))


    @mock.patch('api.converters.output_converters.validate_and_store_resource')
    @mock.patch('api.converters.output_converters.ResourceMetadata')
    @mock.patch('api.converters.output_converters.BaseOutputConverter.create_resource')
    @mock.patch('api.converters.output_converters.delete_resource_by_pk')
    def test_variabledataresource_converts_properly_for_many(self, 
        mock_delete_resource_by_pk,
        mock_create_resource,
        mock_resourcemetadata_model, 
        mock_validate_and_store_resource):
        '''
        When a VariableDataResource is created as part of an ExecutedOperation,
        the outputs give it as a list of objects. Each of those objects has keys 
        of `path` and `resource_type`. 

        The converter's job is to register that as a new file with the workspace
        and return the UUID of this new Resource
        '''

        resource_type = 'MTX'
        other_resource_type = 'I_MTX'

        # this is a real type, but not allowed by the operation spec
        unacceptable_resource_type = 'RNASEQ_COUNT_MTX'

        resource1_uuid = uuid.uuid4()
        resource2_uuid = uuid.uuid4()
        resource3_uuid = uuid.uuid4()

        mock_resource1 = mock.MagicMock()
        mock_resource2 = mock.MagicMock()
        mock_resource3 = mock.MagicMock()
        mock_resource1.resource_type = resource_type
        mock_resource2.resource_type = resource_type
        # note that we don't assign a resource_type to mock_resource3
        mock_resource1.pk = resource1_uuid
        mock_resource2.pk = resource2_uuid
        mock_resource3.pk = resource3_uuid
        mock_create_resource.side_effect = [mock_resource1, mock_resource2]

        mock_resource_metadata_obj1 = mock.MagicMock()
        mock_resource_metadata_obj2 = mock.MagicMock()
        mock_resourcemetadata_model.objects.get.side_effect = [
            mock_resource_metadata_obj1,
            mock_resource_metadata_obj2
        ]

        all_user_workspaces = Workspace.objects.filter(owner=self.regular_user_1)
        if len(all_user_workspaces) < 1:
            raise ImproperlyConfigured('Need at least one Workspace for the regular user.')
        workspace = all_user_workspaces[0]

        c = LocalDockerOutputConverter()
        job_id = str(uuid.uuid4())
        op = Operation.objects.all()[0]
        job_name = 'foo'
        executed_op = WorkspaceExecutedOperation.objects.create(
            id=job_id,
            workspace=workspace,
            owner=self.regular_user_1,
            inputs = {},
            operation = op,
            mode = '',
            job_name = job_name
        )
        output_spec = {
            'attribute_type': 'VariableDataResource',
            'many': True,
            'resource_types': [resource_type, other_resource_type]
        }
        mock_path1 = '/some/output/path1.txt'
        mock_path2 = '/some/output/path2.txt'
        return_val = c.convert_output(executed_op, 
            workspace, 
            output_spec, 
            [
                {
                    'path':mock_path1,
                    'resource_type': resource_type
                },
                {
                    'path':mock_path2,
                    'resource_type': resource_type
                }
            ]
        )

        expected_name1 = '{n}.path1.txt'.format(n=job_name)
        expected_name2 = '{n}.path2.txt'.format(n=job_name)
        call1 = mock.call(
            self.regular_user_1,
            workspace,
            mock_path1,
            expected_name1
        )
        call2 = mock.call(
            self.regular_user_1,
            workspace,
            mock_path2,
            expected_name2
        )
        mock_create_resource.assert_has_calls([
            call1,
            call2
        ])
        self.assertEqual(mock_validate_and_store_resource.call_count, 2)
        self.assertEqual(mock_resourcemetadata_model.objects.get.call_count, 2)
        mock_resource_metadata_obj1.save.assert_called()
        mock_resource_metadata_obj2.save.assert_called()
        self.assertCountEqual(return_val, [str(resource1_uuid), str(resource2_uuid)])

        # reset the mocks:
        mock_validate_and_store_resource.reset_mock()
        mock_resourcemetadata_model.reset_mock()
        mock_create_resource.reset_mock()
        mock_create_resource.side_effect = [mock_resource1,]
        mock_resourcemetadata_model.objects.get.side_effect = [
            mock_resource_metadata_obj1,
        ]
        # call where the second output has a type that is not compatible
        # with the operation spec
        with self.assertRaisesRegex(OutputConversionException, unacceptable_resource_type):
            c.convert_output(executed_op, 
                workspace, 
                output_spec, 
                [
                    {
                        'path':mock_path1,
                        'resource_type': resource_type
                    },
                    {
                        'path':mock_path2,
                        'resource_type': unacceptable_resource_type
                    }
                ]
            )
        # the create_resource method should have been called only once.
        # The second one was given as an unacceptable type so the resource
        # is never created
        expected_name1 = '{n}.path1.txt'.format(n=job_name)
        call1 = mock.call(
            self.regular_user_1,
            workspace,
            mock_path1,
            expected_name1
        )
        mock_create_resource.assert_has_calls([
            call1,
        ])
        
        self.assertEqual(mock_resourcemetadata_model.objects.get.call_count, 1)
        mock_resource_metadata_obj1.save.assert_called()

        # Check that the delete was called on the first one which passed validation-
        # We don't want incomplete outputs.
        mock_delete_resource_by_pk.assert_has_calls([
            mock.call(str(resource1_uuid)),
        ])

        # reset the mocks again
        mock_validate_and_store_resource.reset_mock()
        mock_resourcemetadata_model.reset_mock()
        mock_create_resource.reset_mock()
        mock_delete_resource_by_pk.reset_mock()
        # mock_resource3 does not have the resource_type set
        mock_create_resource.side_effect = [mock_resource1, mock_resource3]
        mock_resourcemetadata_model.objects.get.side_effect = [
            mock_resource_metadata_obj1,
            mock_resource_metadata_obj2
        ]
        # call where the second output has a valid type, but will eventually fail
        # validation. That failure is mocked by not assigning the proper resource_type
        # attribute on the mock return Resource
        with self.assertRaisesRegex(OutputConversionException, other_resource_type):
            c.convert_output(executed_op, 
                workspace, 
                output_spec, 
                [
                    {
                        'path':mock_path1,
                        'resource_type': resource_type
                    },
                    {
                        'path':mock_path2,
                        'resource_type': other_resource_type
                    }
                ]
            )
        # the create_resource method should have been called only once.
        # The second one was given as an unacceptable type so the resource
        # is never created
        expected_name1 = '{n}.path1.txt'.format(n=job_name)
        expected_name2 = '{n}.path2.txt'.format(n=job_name)
        call1 = mock.call(
            self.regular_user_1,
            workspace,
            mock_path1,
            expected_name1
        )
        call2 = mock.call(
            self.regular_user_1,
            workspace,
            mock_path2,
            expected_name2
        )
        mock_create_resource.assert_has_calls([
            call1,
            call2
        ])
        
        # only call the resource metadata once since the second will fail
        self.assertEqual(mock_resourcemetadata_model.objects.get.call_count, 1)
        mock_resource_metadata_obj1.save.assert_called()

        # Check that the delete was called on the first one which passed validation-
        # We don't want incomplete outputs. Here, just ensure the order is same, even
        # though it really does not matter. Just a guard against errors in this unit test.
        mock_delete_resource_by_pk.assert_has_calls([
            mock.call(str(resource3_uuid)),
            mock.call(str(resource1_uuid)),
        ], any_order=False)