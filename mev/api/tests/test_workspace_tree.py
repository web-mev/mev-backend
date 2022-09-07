import unittest.mock as mock
import uuid
import os
import json
import datetime

from django.urls import reverse
from django.core.exceptions import ImproperlyConfigured
from rest_framework import status

from api.models import Workspace, Resource

from api.tests.base import BaseAPITestCase

class TestWorkspaceTree(BaseAPITestCase):
    def setUp(self):
        self.establish_clients()

    @mock.patch('api.views.workspace_tree_views.create_workspace_dag')
    def test_tree_response(self, mock_create_workspace_dag):
        workspaces = Workspace.objects.filter(owner=self.regular_user_1)
        if len(workspaces) == 0:
            raise ImproperlyConfigured('Need at least one workspace to run this')
        workspace = workspaces[0]
        url = reverse(
            'executed-operation-tree', 
            kwargs={'workspace_pk':workspace.pk}
        )
        expected_response = [
            {'id': 'foo'},
            {'id': 'bar'}
        ]
        mock_create_workspace_dag.return_value = expected_response
        response = self.authenticated_regular_client.get(url)
        response_json = response.json() 
        self.assertEqual(expected_response, response_json)       

    @mock.patch('api.views.workspace_tree_views.create_workspace_dag')
    def test_rejects_other_user(self, mock_create_workspace_dag):
        '''
        The workspace is owned by someone else, so the request should fail
        with a 403
        '''
        workspaces = Workspace.objects.filter(owner=self.regular_user_2)
        if len(workspaces) == 0:
            raise ImproperlyConfigured('Need at least one workspace to run this')
        workspace = workspaces[0]
        url = reverse(
            'executed-operation-tree', 
            kwargs={'workspace_pk':workspace.pk}
        )
        response = self.authenticated_regular_client.get(url)
        self.assertEqual(403, response.status_code)  


    @mock.patch('api.views.workspace_tree_views.create_workspace_dag')
    def test_rejects_bad_workspace_uuid(self, mock_create_workspace_dag):
        '''
        The workspace arg doesn't reference a valid workspace
        '''
        url = reverse(
            'executed-operation-tree', 
            kwargs={'workspace_pk':str(uuid.uuid4())}
        )
        response = self.authenticated_regular_client.get(url)
        self.assertEqual(400, response.status_code)  


class TestWorkspaceTreeSave(BaseAPITestCase):
    def setUp(self):
        self.establish_clients()

    @mock.patch('api.views.workspace_tree_views.create_workspace_dag')
    @mock.patch('api.views.workspace_tree_views.datetime')
    @mock.patch('api.views.workspace_tree_views.initiate_resource_validation')
    def test_tree_response(self, mock_initiate_resource_validation, \
        mock_datetime, \
        mock_create_workspace_dag):

        workspaces = Workspace.objects.filter(owner=self.regular_user_1)
        if len(workspaces) == 0:
            raise ImproperlyConfigured('Need at least one workspace to run this')
        workspace = workspaces[0]
        url = reverse(
            'executed-operation-tree-save', 
            kwargs={'workspace_pk':workspace.pk}
        )
        expected_content = [
            {'id': 'foo'},
            {'id': 'bar'}
        ]
        mock_create_workspace_dag.return_value = expected_content

        now = datetime.datetime.now()
        mock_datetime.datetime.now.return_value = now

        # check the number of initial resources for this owner:
        orig_resources = [x.id for x in Resource.objects.filter(owner=self.regular_user_1)]
        response = self.authenticated_regular_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)   

        # get the final resources. Check that we have one more:
        final_resources = [x.id for x in Resource.objects.filter(owner=self.regular_user_1)]

        diff_set = list(set(final_resources).difference(set(orig_resources)))
        self.assertTrue(len(diff_set) == 1)
        new_resource = Resource.objects.get(pk=diff_set[0])

        mock_initiate_resource_validation.assert_called()
        contents = json.load(new_resource.datafile.open('r'))
        self.assertCountEqual(contents, expected_content)

    def test_bad_workspace_id_fails(self):
        url = reverse(
            'executed-operation-tree-save', 
            kwargs={'workspace_pk':str(uuid.uuid4())}
        )
        response = self.authenticated_regular_client.get(url)
        self.assertTrue(response.status_code == 400)