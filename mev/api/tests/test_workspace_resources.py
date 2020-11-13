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
            r = user_workspaces[idx].resources.all()
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
        self.all_workspace_resources = self.demo_workspace.resources.all()

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

class WorkspaceResourceAddTests(BaseAPITestCase):

    def setUp(self):
        self.establish_clients()

        all_resources = Resource.objects.all()
        workspace_resources = []
        active_unattached_resources = []
        for r in all_resources:
            if (r.is_active) and (len(r.workspaces.all()) > 0):
                workspace_resources.append(r)
            elif (r.is_active) and (len(r.workspaces.all()) == 0):
                active_unattached_resources.append(r)
        if len(workspace_resources) == 0:
            raise ImproperlyConfigured('You need at least one'
                ' workspace-associated resource to run the tests.'
                ' in this test case.'
            )
        if len(active_unattached_resources) == 0:
            raise ImproperlyConfigured('Need at least one'
                ' active and unattached Resource to'
                ' run this test.'
            )

        self.workspace_resource = workspace_resources[0]
        assoc_workspaces = self.workspace_resource.workspaces.all()
        self.workspace_pk = assoc_workspaces[0].pk
        self.url = reverse(
            'workspace-resource-add', 
            kwargs={'workspace_pk': self.workspace_pk}
        )

        self.unattached_resource = active_unattached_resources[0]


    def test_attached_resource_does_not_change(self):
        '''
        Tests that a Resource already associated with a Workspace
        can't be added again (i.e. the Resource.workspaces attribute does not
        change if we try to add a Resource to a Workspace again.)
        '''
        orig_workspaces = [x.pk for x in self.workspace_resource.workspaces.all()]
        payload = {'resource_uuid': self.workspace_resource.pk}
        response = self.authenticated_regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        updated_resource = Resource.objects.get(pk=self.workspace_resource.pk)
        final_workspaces = [x.pk for x in updated_resource.workspaces.all()]
        self.assertEqual(orig_workspaces, final_workspaces)

    def test_add_another_workspace(self):
        '''
        Add a second workspace to a particular resource. That is, the user wishes
        to associated a single Resource with two Workspaces
        '''
        # the resource self.workspace_resource already has an associated workspace
        # get a different workspace
        all_user_workspaces = Workspace.objects.filter(owner=self.regular_user_1)
        other_user_workspaces = []
        for w in all_user_workspaces:
            if w.pk != self.workspace_pk:
                other_user_workspaces.append(w)
        if len(other_user_workspaces) == 0:
            raise ImproperlyConfigured('Need another workspace so we can attach our Resource.')

        other_workspace = other_user_workspaces[0]
        self.assertEqual(len(self.workspace_resource.workspaces.all()), 1)
        payload = {'resource_uuid': self.workspace_resource.pk}
        url = reverse(
            'workspace-resource-add', 
            kwargs={'workspace_pk': other_workspace.pk}
        )
        response = self.authenticated_regular_client.post(url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        updated_resource = Resource.objects.get(pk=self.workspace_resource.pk)
        final_workspaces = [x.pk for x in updated_resource.workspaces.all()]
        self.assertEqual(len(final_workspaces),2)
        self.assertCountEqual(final_workspaces, [other_workspace.pk, self.workspace_pk])


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
        inactive_resources = Resource.objects.filter(
            is_active=False,
            owner = self.regular_user_1,
        )
        inactive_unattached_resources = []
        for r in inactive_resources:
            if len(r.workspaces.all()) == 0:
                inactive_unattached_resources.append(r)
        if len(inactive_unattached_resources) == 0:
            raise ImproperlyConfigured('Need at least one'
                ' inactive and unattached Resource to run'
                ' this test.'
            )
        r = inactive_unattached_resources[0]
        payload = {'resource_uuid': r.pk}
        response = self.authenticated_regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_resource_without_type_cannot_be_added(self):
        '''
        Test the situation where a Resource is active but does not have a type set
        (such as when the upload succeeds, but the type they specified was not
        compatible with the file's content).  We can't add this Resource to a workspace
        '''
        active_and_unset_resources = Resource.objects.filter(
            is_active=True,
            owner = self.regular_user_1,
            resource_type=None
        )
        active_unattached_and_unset_resources = []
        for r in active_and_unset_resources:
            if len(r.workspaces.all()) == 0:
                active_unattached_and_unset_resources.append(r)

        if len(active_unattached_and_unset_resources) == 0:
            raise ImproperlyConfigured('Need at least one'
                ' active, unattached, and unset Resource to run'
                ' this test.'
            )
        r = active_unattached_and_unset_resources[0]
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


    def test_correct_request_adds_workspace(self):
        '''
        Test that the endpoint returns a 201 if the request
        was correct and the resource was added to the workspace
        '''

        # need an active, unattached resource with a type:
        active_typed_resources = Resource.objects.filter(
            is_active=True
        ).exclude(resource_type__isnull=True)
        active_unattached_resources = []
        for r in active_typed_resources:
            if len(r.workspaces.all()) == 0:
                active_unattached_resources.append(r)
        
        if len(active_unattached_resources) == 0:
            raise ImproperlyConfigured('Need an active, unattached'
                ' resource with a type specified to run this test.'
            )
        r = active_unattached_resources[0]
        self.assertTrue(len(r.workspaces.all()) == 0)
        payload = {'resource_uuid': r.pk}
        response = self.authenticated_regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # query to check that the workspace was added
        r = Resource.objects.get(pk=r.pk)
        assoc_workspaces = [x.pk for x in r.workspaces.all()]
        self.assertTrue(len(assoc_workspaces) == 1)
        expected_workspace_pk = assoc_workspaces[0]
        self.assertEqual(expected_workspace_pk, self.workspace_pk)