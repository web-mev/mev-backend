import uuid

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