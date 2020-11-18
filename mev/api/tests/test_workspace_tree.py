import unittest.mock as mock

from django.urls import reverse
from django.core.exceptions import ImproperlyConfigured

from api.models import Workspace

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