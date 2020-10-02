import unittest
import unittest.mock as mock
import os
import json
import uuid

from django.core.exceptions import ImproperlyConfigured
from api.tests.base import BaseAPITestCase
from api.models import Workspace, Resource

from api.converters.output_converters import LocalDockerOutputConverter

class ExecutedOperationOutputConverterTester(BaseAPITestCase):

    def setUp(self):
        self.establish_clients()

    @mock.patch('api.converters.output_converters.validate_and_store_resource')
    def test_dataresource_converts_properly(self, mock_validate_and_store_resource):
        '''
        When a DataResource is created as part of an ExecutedOperation,
        the outputs give it as a path (or list of paths)

        The converter's job is to register that as a new file with the workspace
        and return the UUID of this new Resource
        '''

        # get the  initial counts on the database entities:
        all_user_resources = Resource.objects.filter(owner=self.regular_user_1)
        n0 = len(all_user_resources)
        all_user_workspaces = Workspace.objects.filter(owner=self.regular_user_1)
        if len(all_user_workspaces) < 1:
            raise ImproperlyConfigured('Need at least one Workspace for the regular user.')
        workspace = all_user_workspaces[0]
        workspace_resources = Resource.objects.filter(workspace=workspace)
        w0 = len(workspace_resources)

        c = LocalDockerOutputConverter()
        job_id = str(uuid.uuid4())
        output_spec = {
            'attribute_type': 'DataResource',
            'many': False,
            'resource_type': 'MTX'
        }
        c.convert_output(job_id, workspace, output_spec, '/some/output/path.txt')

        mock_validate_and_store_resource.assert_called()

        # query the Resources again:
        updated_all_user_resources = Resource.objects.filter(owner=self.regular_user_1)
        n1 = len(updated_all_user_resources)
        self.assertEqual(n1-n0, 1)
        updated_workspace_resources = Resource.objects.filter(workspace=workspace)
        w1 = len(updated_workspace_resources)
        self.assertEqual(w1-w0, 1)

        expected_name = '{id}.path.txt'.format(id=job_id)
        r = Resource.objects.filter(name=expected_name )
        self.assertTrue(len(r) == 1)




    