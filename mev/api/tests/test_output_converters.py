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

class ExecutedOperationOutputConverterTester(BaseAPITestCase):

    def setUp(self):
        self.establish_clients()

    @mock.patch('api.converters.output_converters.validate_and_store_resource')
    @mock.patch('api.converters.output_converters.ResourceMetadata')
    def test_dataresource_converts_properly(self, mock_resourcemetadata_model, mock_validate_and_store_resource):
        '''
        When a DataResource is created as part of an ExecutedOperation,
        the outputs give it as a path (or list of paths). Here we test the single value

        The converter's job is to register that as a new file with the workspace
        and return the UUID of this new Resource
        '''
        mock_resource_metadata_obj = mock.MagicMock()
        mock_resourcemetadata_model.objects.get.return_value = mock_resource_metadata_obj

        # get the  initial counts on the database entities:
        all_user_resources = Resource.objects.filter(owner=self.regular_user_1)
        n0 = len(all_user_resources)
        all_user_workspaces = Workspace.objects.filter(owner=self.regular_user_1)
        if len(all_user_workspaces) < 1:
            raise ImproperlyConfigured('Need at least one Workspace for the regular user.')
        workspace = all_user_workspaces[0]
        workspace_resources = workspace.resources.all()
        w0 = len(workspace_resources)

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
            'resource_type': 'MTX'
        }
        c.convert_output(executed_op, workspace, output_spec, '/some/output/path.txt')

        mock_validate_and_store_resource.assert_called()
        mock_resourcemetadata_model.objects.get.assert_called()
        mock_resource_metadata_obj.save.assert_called()

        # query the Resources again:
        updated_all_user_resources = Resource.objects.filter(owner=self.regular_user_1)
        n1 = len(updated_all_user_resources)
        self.assertEqual(n1-n0, 1)
        updated_workspace_resources = workspace.resources.all()
        w1 = len(updated_workspace_resources)
        self.assertEqual(w1-w0, 1)

        expected_name = '{n}.path.txt'.format(n=job_name)
        r = Resource.objects.filter(name=expected_name )
        self.assertTrue(len(r) == 1)

        r = r[0]
        resource_workspaces = r.workspaces.all()
        self.assertTrue(workspace in resource_workspaces)

    @mock.patch('api.converters.output_converters.validate_and_store_resource')
    @mock.patch('api.converters.output_converters.ResourceMetadata')
    def test_dataresource_converts_list_properly(self, mock_resourcemetadata_model, mock_validate_and_store_resource):
        '''
        When a DataResource is created as part of an ExecutedOperation,
        the outputs give it as a path (or list of paths). Here we test the list of paths

        The converter's job is to register that as a new file with the workspace
        and return the UUID of this new Resources
        '''
        mock_resource_metadata_obj1 = mock.MagicMock()
        mock_resource_metadata_obj2 = mock.MagicMock()
        mock_resourcemetadata_model.objects.get.side_effect = [
            mock_resource_metadata_obj1,
            mock_resource_metadata_obj2
        ]

        # get the  initial counts on the database entities:
        all_user_resources = Resource.objects.filter(owner=self.regular_user_1)
        n0 = len(all_user_resources)
        all_user_workspaces = Workspace.objects.filter(owner=self.regular_user_1)
        if len(all_user_workspaces) < 1:
            raise ImproperlyConfigured('Need at least one Workspace for the regular user.')
        workspace = all_user_workspaces[0]
        workspace_resources = workspace.resources.all()
        w0 = len(workspace_resources)

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
            'resource_type': 'MTX'
        }
        c.convert_output(executed_op, 
            workspace, 
            output_spec, 
            [
                '/some/output/path1.txt',
                '/some/output/path2.txt'
            ]
        )

        mock_validate_and_store_resource.assert_called()
        self.assertEqual(mock_resourcemetadata_model.objects.get.call_count, 2)
        mock_resource_metadata_obj1.save.assert_called()
        mock_resource_metadata_obj2.save.assert_called()

        # query the Resources again:
        updated_all_user_resources = Resource.objects.filter(owner=self.regular_user_1)
        n1 = len(updated_all_user_resources)
        self.assertEqual(n1-n0, 2)
        updated_workspace_resources = workspace.resources.all()
        w1 = len(updated_workspace_resources)
        self.assertEqual(w1-w0, 2)

        # check that we entered the correct things into the database for both files
        # and that they are associated with the proper workspace
        expected_name = '{n}.path1.txt'.format(n=job_name)
        r = Resource.objects.filter(name=expected_name )
        self.assertTrue(len(r) == 1)
        r = r[0]
        resource_workspaces = r.workspaces.all()
        self.assertTrue(workspace in resource_workspaces)

        expected_name = '{n}.path2.txt'.format(n=job_name)
        r = Resource.objects.filter(name=expected_name )
        self.assertTrue(len(r) == 1)
        r = r[0]
        resource_workspaces = r.workspaces.all()
        self.assertTrue(workspace in resource_workspaces)

    @mock.patch('api.converters.output_converters.validate_and_store_resource')
    @mock.patch('api.converters.output_converters.ResourceMetadata')
    def test_dataresource_converts_properly_case2(self, mock_resourcemetadata_model, mock_validate_and_store_resource):
        '''
        When a DataResource is created as part of an ExecutedOperation,
        the outputs give it as a path (or list of paths)

        The converter's job is to register that as a new file with the workspace
        and return the UUID of this new Resource

        Here, we have a non-workspace Op, so we check that we only create a Resource
        but do not associate it with any Workspaces
        '''
        mock_resource_metadata_obj = mock.MagicMock()
        mock_resourcemetadata_model.objects.get.return_value = mock_resource_metadata_obj

        # get the initial counts on the database entities:
        all_user_resources = Resource.objects.filter(owner=self.regular_user_1)
        n0 = len(all_user_resources)
        all_user_workspaces = Workspace.objects.filter(owner=self.regular_user_1)
        if len(all_user_workspaces) < 1:
            raise ImproperlyConfigured('Need at least one Workspace for the regular user.')

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
            'resource_type': 'MTX'
        }
        c.convert_output(executed_op, None, output_spec, '/some/output/path.txt')

        mock_validate_and_store_resource.assert_called()
        mock_resourcemetadata_model.objects.get.assert_called()
        mock_resource_metadata_obj.save.assert_called()

        # query the Resources again:
        updated_all_user_resources = Resource.objects.filter(owner=self.regular_user_1)
        n1 = len(updated_all_user_resources)
        self.assertEqual(n1-n0, 1)

        # since there was no job name, there is no prefix
        expected_name = 'path.txt'
        r = Resource.objects.filter(name=expected_name )
        self.assertTrue(len(r) == 1)

        r = r[0]
        resource_workspaces = r.workspaces.all()
        self.assertTrue(len(resource_workspaces) == 0)


class VariableDataResourceOutputConverterTester(BaseAPITestCase):

    def setUp(self):
        self.establish_clients()

    @mock.patch('api.converters.output_converters.validate_and_store_resource')
    @mock.patch('api.converters.output_converters.ResourceMetadata')
    def test_variabledataresource_converts_properly(self, mock_resourcemetadata_model, mock_validate_and_store_resource):
        '''
        When a VariableDataResource is created as part of an ExecutedOperation,
        the outputs give it as an object with keys of `path` and `resource_type`. 
        Recall that VariableDataResource instances allow us to dynamically set the 
        resource type of the output files.

        The converter's job is to register that as a new file with the workspace
        and return the UUID of this new Resource
        '''
        mock_resource_metadata_obj = mock.MagicMock()
        mock_resourcemetadata_model.objects.get.return_value = mock_resource_metadata_obj

        # get the  initial counts on the database entities:
        all_user_resources = Resource.objects.filter(owner=self.regular_user_1)
        n0 = len(all_user_resources)
        all_user_workspaces = Workspace.objects.filter(owner=self.regular_user_1)
        if len(all_user_workspaces) < 1:
            raise ImproperlyConfigured('Need at least one Workspace for the regular user.')
        workspace = all_user_workspaces[0]
        workspace_resources = workspace.resources.all()
        w0 = len(workspace_resources)

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
        with self.assertRaises(ValidationError):
            c.convert_output(executed_op, workspace, output_spec, '/some/output/path.txt')

        # try with a dict, but one that does not have the correct keys 
        # (missing the resource_type key)
        with self.assertRaisesRegex(ValidationError, 'resource_type') as ex:
            c.convert_output(executed_op, workspace, output_spec, 
                {
                    'path':'/some/output/path.txt',
                }
            )

        # try with a dict, but one that does not have the correct keys 
        # (missing the path key)
        with self.assertRaisesRegex(ValidationError, 'path') as ex:
            c.convert_output(executed_op, workspace, output_spec, 
                {
                    'pathS':'/some/output/path.txt',
                    'resource_type': 'MTX'
                }
            )

        # a resource_type that doesn't match the spec
        with self.assertRaisesRegex(ValidationError, 'ANN'):
            c.convert_output(executed_op, workspace, output_spec, 
                {
                    'path':'/some/output/path.txt',
                    'resource_type': 'ANN'
                }
            )

        # the output is a list (with many =False)
        with self.assertRaisesRegex(ValidationError, 'dict'):
            c.convert_output(executed_op, workspace, output_spec, 
                [{
                    'path':'/some/output/path.txt',
                    'resource_type': 'ANN'
                },]
            )
        # a good request- has the proper format for the output and the resource_type is 
        # permitted (based on the output_spec)
        c.convert_output(executed_op, workspace, output_spec, 
            {
                'path':'/some/output/path.txt',
                'resource_type': 'MTX'
            }
        )

        mock_validate_and_store_resource.assert_called()
        mock_resourcemetadata_model.objects.get.assert_called()
        mock_resource_metadata_obj.save.assert_called()

        # query the Resources again:
        updated_all_user_resources = Resource.objects.filter(owner=self.regular_user_1)
        n1 = len(updated_all_user_resources)
        self.assertEqual(n1-n0, 1)
        updated_workspace_resources = workspace.resources.all()
        w1 = len(updated_workspace_resources)
        self.assertEqual(w1-w0, 1)

        expected_name = '{n}.path.txt'.format(n=job_name)
        r = Resource.objects.filter(name=expected_name )
        self.assertTrue(len(r) == 1)

        r = r[0]
        resource_workspaces = r.workspaces.all()
        self.assertTrue(workspace in resource_workspaces)

    @mock.patch('api.converters.output_converters.validate_and_store_resource')
    @mock.patch('api.converters.output_converters.ResourceMetadata')
    def test_variabledataresource_converts_properly_for_many(self, mock_resourcemetadata_model, mock_validate_and_store_resource):
        '''
        When a VariableDataResource is created as part of an ExecutedOperation,
        the outputs give it as a list of objects. Each of those objects has keys 
        of `path` and `resource_type`. 

        The converter's job is to register that as a new file with the workspace
        and return the UUID of this new Resource
        '''

        mock_resource_metadata_obj1 = mock.MagicMock()
        mock_resource_metadata_obj2 = mock.MagicMock()
        mock_resourcemetadata_model.objects.get.side_effect = [
            mock_resource_metadata_obj1,
            mock_resource_metadata_obj2
        ]
        # get the  initial counts on the database entities:
        all_user_resources = Resource.objects.filter(owner=self.regular_user_1)
        n0 = len(all_user_resources)
        all_user_workspaces = Workspace.objects.filter(owner=self.regular_user_1)
        if len(all_user_workspaces) < 1:
            raise ImproperlyConfigured('Need at least one Workspace for the regular user.')
        workspace = all_user_workspaces[0]
        workspace_resources = workspace.resources.all()
        w0 = len(workspace_resources)

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
            'resource_types': ['MTX', 'I_MTX']
        }

        # try with a string- should raise an exception since the resource type is not known
        # otherwise. (it should be a list of dicts)
        with self.assertRaises(ValidationError):
            c.convert_output(executed_op, workspace, output_spec, '/some/output/path.txt')

        # try with a dict. should raise exception since it should be a list
        with self.assertRaisesRegex(ValidationError, 'list') as ex:
            c.convert_output(executed_op, workspace, output_spec, 
                {
                    'path':'/some/output/path.txt',
                    'resource_type': 'MTX'
                }
            )

        # a resource_type that doesn't match the spec
        with self.assertRaisesRegex(ValidationError, 'ANN'):
            c.convert_output(executed_op, workspace, output_spec, 
                [
                    {
                        'path':'/some/output/path.txt',
                        'resource_type': 'ANN'
                    }
                ]
            )

        # a good request- has the proper format for the output and the resource_type is 
        # permitted (based on the output_spec)
        c.convert_output(executed_op, workspace, output_spec, 
            [
                {
                    'path':'/some/output/path0.txt',
                    'resource_type': 'MTX'
                }
            ]
        )

        mock_validate_and_store_resource.assert_called()
        mock_resourcemetadata_model.objects.get.assert_called()
        mock_resource_metadata_obj.save.assert_called()

        # query the Resources again:
        updated_all_user_resources = Resource.objects.filter(owner=self.regular_user_1)
        n1 = len(updated_all_user_resources)
        self.assertEqual(n1-n0, 1)
        updated_workspace_resources = workspace.resources.all()
        w1 = len(updated_workspace_resources)
        self.assertEqual(w1-w0, 1)

        expected_name = '{n}.path0.txt'.format(n=job_name)
        r = Resource.objects.filter(name=expected_name )
        self.assertTrue(len(r) == 1)

        r = r[0]
        resource_workspaces = r.workspaces.all()
        self.assertTrue(workspace in resource_workspaces)


        # another good request- has the proper format for the 
        # output and the resource_type is 
        # permitted (based on the output_spec)
        c.convert_output(executed_op, workspace, output_spec, 
            [
                {
                    'path':'/some/output/path1.txt',
                    'resource_type': 'MTX'
                },
                {
                    'path':'/some/output/path2.txt',
                    'resource_type': 'MTX'
                }
            ]
        )
                
        self.assertEqual(mock_validate_and_store_resource.call_count, 2)
        self.assertEqual(mock_resourcemetadata_model.objects.get.call_count, 2)
        mock_resource_metadata_obj1.save.assert_called()
        mock_resource_metadata_obj2.save.assert_called()

        # query the Resources again:
        n0 = len(Resource.objects.filter(owner=self.regular_user_1))
        updated_all_user_resources = Resource.objects.filter(owner=self.regular_user_1)
        n1 = len(updated_all_user_resources)
        self.assertEqual(n1-n0, 2)
        updated_workspace_resources = workspace.resources.all()
        w1 = len(updated_workspace_resources)
        self.assertEqual(w1-w0, 2)

        expected_name = '{n}.path1.txt'.format(n=job_name)
        r = Resource.objects.filter(name=expected_name )
        self.assertTrue(len(r) == 1)

        r = r[0]
        resource_workspaces = r.workspaces.all()
        self.assertTrue(workspace in resource_workspaces)

        expected_name = '{n}.path2.txt'.format(n=job_name)
        r = Resource.objects.filter(name=expected_name )
        self.assertTrue(len(r) == 1)

        r = r[0]
        resource_workspaces = r.workspaces.all()
        self.assertTrue(workspace in resource_workspaces)

    