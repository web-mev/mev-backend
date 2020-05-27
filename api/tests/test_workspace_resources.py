import uuid
import unittest.mock as mock

from django.urls import reverse
from django.core.exceptions import ImproperlyConfigured
from rest_framework import status

from api.models import Resource, Workspace
from api.tests.base import BaseAPITestCase


class WorkspaceResourceListTests(BaseAPITestCase):

    def setUp(self):

        self.establish_clients()

        # get all resources for a regular user
        self.regular_user_resources = Resource.objects.filter(
            owner=self.regular_user_1
        )

        # get the workspaces for this user:
        user_workspaces = Workspace.objects.filter(owner=self.regular_user_1)
        if len(user_workspaces) == 0:
            msg = '''
                Testing not setup correctly.  Please ensure that there is at least one
                Workspace for user {user}.
            '''.format(user=self.regular_user_1)
            raise ImproperlyConfigured(msg)

        # find a Workspace that has some associated Resources
        found_non_empty_workspace = False
        idx = 0
        while (not found_non_empty_workspace) and (idx < len(user_workspaces)):
            r = user_workspaces[idx].workspace_resources.all()
            if len(r) > 0:
                found_non_empty_workspace = True
            else:
                idx += 1
        if not found_non_empty_workspace:
            msg = '''
                Testing not setup correctly.  Please ensure that there is at least one
                Resource instance for the user {user} that is attached to a workspace.
            '''.format(user=self.regular_user_1)
            raise ImproperlyConfigured(msg)

        # now get the Workspace and a list of the Resources attached to that Workspace.
        self.demo_workspace = user_workspaces[idx]
        self.all_workspace_resources = self.demo_workspace.workspace_resources.all()

        self.url = reverse(
            'workspace-resource-list', 
            kwargs={'workspace_pk':self.demo_workspace.pk}
        )


    def test_list_resource_requires_auth(self):
        """
        Test that general requests to the endpoint generate 401
        """
        response = self.regular_client.get(self.url)
        self.assertTrue((response.status_code == status.HTTP_401_UNAUTHORIZED) 
        | (response.status_code == status.HTTP_403_FORBIDDEN))


    def test_admin_can_list_resource(self):
        """
        Test that admins can see all Resources for the Workspace.  Checks by comparing
        the pk (a UUID) between the database instances and those in the response.
        """
        response = self.authenticated_admin_client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # all Resources owned by this user
        all_known_user_uuids = set([str(x.pk) for x in self.regular_user_resources])

        # all Resources associated with the workspace
        all_workspace_uuids = set([str(x.pk) for x in self.all_workspace_resources])

        # those resource UUIDs received in the response
        received_resource_uuids = set([x['id'] for x in response.data])
        self.assertEqual(all_workspace_uuids, received_resource_uuids)

        # check that the test was not trivial and there were some other Resources
        # not associated with this workspace (but owned by the same user)
        self.assertTrue(
            len(all_known_user_uuids.difference(all_workspace_uuids))>0
        )


    def test_invalid_workspace_uuid_raises_exception(self):
        """
        Test that a bad workspace UUID raises an exception
        """
        bad_url = reverse(
            'workspace-resource-list', 
            kwargs={'workspace_pk': uuid.uuid4()}
        )
        response = self.authenticated_admin_client.get(bad_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


    def test_users_can_list_resource(self):
        """
        Test that regular users can list properly
        """
        response = self.authenticated_regular_client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # all Resources owned by this user
        all_known_user_uuids = set([str(x.pk) for x in self.regular_user_resources])

        # all Resources associated with the workspace
        all_workspace_uuids = set([str(x.pk) for x in self.all_workspace_resources])

        # those resource UUIDs received in the response
        received_resource_uuids = set([x['id'] for x in response.data])
        self.assertEqual(all_workspace_uuids, received_resource_uuids)

        # check that the test was not trivial and there were some other Resources
        # not associated with this workspace (but owned by the same user)
        self.assertTrue(
            len(all_known_user_uuids.difference(all_workspace_uuids))>0
        )

        uuid_universe = set([str(x.pk) for x in Resource.objects.all()])
        # check that the test was not trivial and there were some other Resources
        # not owned by this user
        self.assertTrue(
            len(uuid_universe.difference(all_known_user_uuids))>0
        )

class WorkpaceResourceAddTests(BaseAPITestCase):

    def setUp(self):
        self.establish_clients()

        all_resources = Resource.objects.all()
        workspace_resources = []
        for r in all_resources:
            if r.workspace:
                workspace_resources.append(r)

        if len(workspace_resources) == 0:
            raise ImproperlyConfigured('You need at least one'
                ' workspace-associated resource to run the tests.'
                ' in this test case.'
            )
        
        self.workspace_resource = workspace_resources[0]
        workspace_pk = self.workspace_resource.workspace.pk
        self.url = reverse(
            'workspace-resource-add', 
            kwargs={'workspace_pk': workspace_pk}
        )

        active_unattached_resources = Resource.objects.filter(
            is_active=True,
            owner = self.regular_user_1,
            workspace = None
        )
        if len(active_unattached_resources) == 0:
            raise ImproperlyConfigured('Need at least one'
                ' active and unattached Resource to'
                ' run this test.'
            )
        self.unattached_resource = active_unattached_resources[0]


    def test_attached_resource_rejected(self):
        '''
        Tests that a Resource already associated with a Workspace
        can't be added
        '''
        payload = {'resource_uuid': self.workspace_resource.pk}
        response = self.authenticated_regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


    def test_malformatted_request_fails(self):
        '''
        Tests the serializer and an incorrect payload
        '''
        # the key of the payload is bad--
        payload = {'resource_pk': self.workspace_resource.pk}
        response = self.authenticated_regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


    def test_bad_resource_pk_fails(self):
        '''
        Test that posting a bad resource UUID causes the 
        request to fail.
        '''
        payload = {'resource_uuid': str(uuid.uuid4())}
        response = self.authenticated_regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_add_inactive_resource(self):
        '''
        Test that an inactive resource can't be added to
        a workspace (since it may be performing validation, etc.)
        Only active and validated resources can be attached
        to workspaces.
        '''
        inactive_unattached_resources = Resource.objects.filter(
            is_active=False,
            owner = self.regular_user_1,
            workspace = None
        )
        if len(inactive_unattached_resources) == 0:
            raise ImproperlyConfigured('Need at least one'
                ' inactive and unattached Resource to run'
                ' this test.'
            )
        r = inactive_unattached_resources[0]
        payload = {'resource_uuid': r.pk}
        response = self.authenticated_regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


    def test_workspace_and_resource_owner_different_raises_ex(self):
        '''
        If the owner of the workspace and the resource are not the
        same, reject the request.
        '''
        other_user_workspaces = Workspace.objects.filter(owner=self.regular_user_2)
        if len(other_user_workspaces) == 0:
            raise ImproperlyConfigured('Need at least one Workspace'
                ' owned by a different user to run this test.'
            )
        other_user_workspace_pk = other_user_workspaces[0].pk
        url = reverse(
            'workspace-resource-add', 
            kwargs={'workspace_pk': other_user_workspace_pk}
        )
        payload = {'resource_uuid': self.unattached_resource.pk}
        response = self.authenticated_regular_client.post(url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


    @mock.patch('api.views.workspace_resource_views.copy_resource_to_workspace')
    def test_correct_request_yields_object_creation(self, mock_copy):
        '''
        Test that the endpoint returns a 201 if the request
        was correct and the resource was added to the workspace
        '''
        mock_new_resource = Resource.objects.create(
            path='/path/to/foo.tsv',
            name = 'foo.tsv',
            owner = self.regular_user_1,
            workspace = self.workspace_resource.workspace,
            resource_type = 'MTX',
        )
        mock_copy.return_value = mock_new_resource

        payload = {'resource_uuid': self.unattached_resource.pk}
        response = self.authenticated_regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)