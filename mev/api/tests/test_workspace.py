from django.urls import reverse
from django.core.exceptions import ImproperlyConfigured
from rest_framework import status

from api.models import Workspace
from api.tests.base import BaseAPITestCase
from api.tests import test_settings


class WorkspaceListTests(BaseAPITestCase):

    def setUp(self):

        self.url = reverse('workspace-list')
        self.establish_clients()

    def test_list_workspace_requires_auth(self):
        """
        Test that general requests to the endpoint generate 401
        """
        response = self.regular_client.get(self.url)
        self.assertTrue((response.status_code == status.HTTP_401_UNAUTHORIZED) 
        | (response.status_code == status.HTTP_403_FORBIDDEN))

    def test_admin_can_list_workspace(self):
        """
        Test that admins can see all Workpaces.  Checks by comparing
        the pk (a UUID) between the database instances and those in the response.
        """
        response = self.authenticated_admin_client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        all_known_workspace_uuids = set([str(x.pk) for x in Workspace.objects.all()])
        received_workspace_uuids = set([x['id'] for x in response.data])
        self.assertEqual(all_known_workspace_uuids, received_workspace_uuids)

    def test_admin_can_create_workspace(self):
        """
        Test that admins can create a Workpace.
        """
        # get all initial instances before anything happens:
        initial_workspace_uuids = set([str(x.pk) for x in Workspace.objects.all()])

        payload = {'owner_email': self.regular_user_1.email}
        response = self.authenticated_admin_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # get current instances:
        current_workspace_uuids = set([str(x.pk) for x in Workspace.objects.all()])
        difference_set = current_workspace_uuids.difference(initial_workspace_uuids)
        self.assertEqual(len(difference_set), 1)

    def test_admin_sending_bad_email_raises_error(self):
        """
        Test that admins providing a bad email (a user who is not in the db) raises 400
        """
        # get all initial instances before anything happens:
        initial_workspace_uuids = set([str(x.pk) for x in Workspace.objects.all()])

        payload = {'owner_email': test_settings.JUNK_EMAIL}
        response = self.authenticated_admin_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # get current instances to check none were created:
        current_workspace_uuids = set([str(x.pk) for x in Workspace.objects.all()])
        difference_set = current_workspace_uuids.difference(initial_workspace_uuids)
        self.assertEqual(len(difference_set), 0)

    def test_user_sending_bad_email_raises_error(self):
        """
        Test that regular users specifying a bad email (a user who
        does not exist in the db) generates an error
        """
        # get all initial instances before anything happens:
        initial_workspace_uuids = set([str(x.pk) for x in Workspace.objects.all()])

        payload = {'owner_email': test_settings.JUNK_EMAIL}
        response = self.authenticated_regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # get current instances to check none were created:
        current_workspace_uuids = set([str(x.pk) for x in Workspace.objects.all()])
        difference_set = current_workspace_uuids.difference(initial_workspace_uuids)
        self.assertEqual(len(difference_set), 0)


    def test_users_can_list_workspace(self):
        """
        Test that regular users can list ONLY their own workspaces
        """
        response = self.authenticated_regular_client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        all_known_workspace_uuids = set([str(x.pk) for x in Workspace.objects.all()])
        personal_workspaces = Workspace.objects.filter(owner=self.regular_user_1)
        personal_workspace_uuids = set([str(x.pk) for x in personal_workspaces])
        received_workspace_uuids = set([x['id'] for x in response.data])

        # checks that the test below is not trivial.  i.e. there are Workspaces owned by OTHER users
        self.assertTrue(len(all_known_workspace_uuids.difference(personal_workspace_uuids)) > 0)

        # checks that they only get their own workspaces (by checking UUID)
        self.assertEqual(personal_workspace_uuids, received_workspace_uuids)

    def test_user_can_create_workspace_for_self(self):
        """
        Test that users can create a Workpace for themself.
        Here they set the name explicitly
        """
        # get all initial instances before anything happens:
        initial_workspace_uuids = set([str(x.pk) for x in Workspace.objects.all()])

        expected_name = 'foo'
        payload = {'owner_email': self.regular_user_1.email, 'workspace_name': expected_name}
        response = self.authenticated_regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        j = response.json()
        new_uuid = j['id']

        # get current instances:
        current_workspace_uuids = set([str(x.pk) for x in Workspace.objects.all()])
        difference_set = current_workspace_uuids.difference(initial_workspace_uuids)
        self.assertEqual(len(difference_set), 1)

        self.assertEqual(list(difference_set)[0], new_uuid)
        new_workspace = Workspace.objects.get(pk=new_uuid)
        self.assertEqual(new_workspace.workspace_name, expected_name)

    def test_duplicate_workspace_name_handled(self):
        """
        Test that we handle the request to create a new workspace appropriately if another workspace
        with that name already exists
        """
        # first create a workspace with name 'foo'. Then try to create another.

        # get all initial instances before anything happens:
        initial_workspace_uuids = set([str(x.pk) for x in Workspace.objects.all()])

        expected_name = 'foo'
        payload = {'owner_email': self.regular_user_1.email, 'workspace_name': expected_name}
        response = self.authenticated_regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.authenticated_regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue('workspace_name' in response.json())


    def test_user_can_create_workspace_for_self_no_name(self):
        """
        Test that users can create a Workpace for themself.
        Here they do NOT set the name and we check that it was auto-assigned
        """
        # get all initial instances before anything happens:
        initial_workspace_uuids = set([str(x.pk) for x in Workspace.objects.all()])

        payload = {'owner_email': self.regular_user_1.email}
        response = self.authenticated_regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        j = response.json()
        new_uuid = j['id']

        # get current instances:
        current_workspace_uuids = set([str(x.pk) for x in Workspace.objects.all()])
        difference_set = current_workspace_uuids.difference(initial_workspace_uuids)
        self.assertEqual(len(difference_set), 1)

        self.assertEqual(list(difference_set)[0], new_uuid)
        new_workspace = Workspace.objects.get(pk=new_uuid)
        self.assertEqual(new_workspace.workspace_name, new_uuid)


    def test_user_cannot_create_workspace_for_other(self):
        """
        Test that users can NOT create a Workpace for someone else

        The supplied email for the 'other' user below is valid
        """
        # get all initial instances before anything happens:
        initial_workspace_uuids = set([str(x.pk) for x in Workspace.objects.all()])

        payload = {'owner_email': self.regular_user_2.email}
        response = self.authenticated_regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # get current instances, to ensure nothing new was added:
        current_workspace_uuids = set([str(x.pk) for x in Workspace.objects.all()])
        difference_set = current_workspace_uuids.difference(initial_workspace_uuids)
        self.assertEqual(len(difference_set), 0)


class WorkspaceDetailTests(BaseAPITestCase):

    def setUp(self):

        self.establish_clients()

        # get an example from the database:
        regular_user_workspaces = Workspace.objects.filter(owner=self.regular_user_1)
        if len(regular_user_workspaces) == 0:
            msg = '''
                Testing not setup correctly.  Please ensure that there is at least one
                Workspace instance for the user {user}
            '''.format(user=self.regular_user_1)
            raise ImproperlyConfigured(msg)
        # just take the first Workspace for this user
        self.regular_user_workspace = regular_user_workspaces[0]
        self.url = reverse('workspace-detail', kwargs={'pk':self.regular_user_workspace.pk})

    def test_workspace_detail_requires_auth(self):
        """
        Test that general requests to the endpoint generate 401
        """
        response = self.regular_client.get(self.url)
        self.assertTrue((response.status_code == status.HTTP_401_UNAUTHORIZED) 
        | (response.status_code == status.HTTP_403_FORBIDDEN))

    def test_admin_can_view_workspace_detail(self):
        """
        Test that admins can view the Workpace detail for anyone
        """
        response = self.authenticated_admin_client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(str(self.regular_user_workspace.pk), response.data['id'])

    def test_admin_can_delete_workspace(self):
        """
        Test that admin users can delete any Workpace.
        """
        response = self.authenticated_admin_client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        with self.assertRaises(Workspace.DoesNotExist):
            Workspace.objects.get(pk=self.regular_user_workspace.pk)

    def test_users_can_view_own_workspace_detail(self):
        """
        Test that regular users can view their own Workpace detail.
        """
        response = self.authenticated_regular_client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(str(self.regular_user_workspace.pk), response.data['id'])

    def test_users_can_delete_own_workspace(self):
        """
        Test that regular users can delete their own Workpace.
        """
        response = self.authenticated_regular_client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        with self.assertRaises(Workspace.DoesNotExist):
            Workspace.objects.get(pk=self.regular_user_workspace.pk)

    def test_other_users_cannot_delete_workspace(self):
        """
        Test that another regular users can't delete someone else's Workpace.
        """
        response = self.authenticated_other_client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_other_user_cannot_view_workspace_detail(self):
        """
        Test that another regular user can't view the Workpace detail.
        """
        response = self.authenticated_other_client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_users_can_edit_own_workspace_detail(self):
        """
        Test that regular users can edit their own Workpace detail.
        """
        new_name = 'My new workspace name'

        # initially check that the names are different:
        self.assertTrue(self.regular_user_workspace.workspace_name != new_name)

        payload = {'workspace_name':new_name, 'owner_email':self.regular_user_1.email}
        response = self.authenticated_regular_client.put(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(new_name, response.data['workspace_name'])

        # also query DB to make sure it changed there:
        pk = self.regular_user_workspace.pk
        w = Workspace.objects.get(pk=pk)
        self.assertEqual(w.workspace_name, new_name)

        # try editing via PATCH:
        new_name = 'Another new workspace name'
        self.assertTrue(self.regular_user_workspace.workspace_name != new_name)
        payload = {'workspace_name':new_name, 'owner_email':self.regular_user_1.email}
        response = self.authenticated_regular_client.patch(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(new_name, response.data['workspace_name'])

        # also query DB to make sure it changed there:
        pk = self.regular_user_workspace.pk
        w = Workspace.objects.get(pk=pk)
        self.assertEqual(w.workspace_name, new_name)

        # check that the owner_email field is indeed unnecesary:
        new_name = 'Yet another new workspace name'
        self.assertTrue(self.regular_user_workspace.workspace_name != new_name)
        payload = {'workspace_name':new_name}
        response = self.authenticated_regular_client.put(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(new_name, response.data['workspace_name'])

    def test_others_cannot_edit_workspace_detail(self):
        """
        Test that regular users can't edit the Workpace details of others.
        """
        new_name = 'My new workspace name'

        # initially check that the names are different:
        self.assertTrue(self.regular_user_workspace.workspace_name != new_name)

        payload = {'workspace_name':new_name, 'owner_email':self.regular_user_1.email}
        response = self.authenticated_other_client.put(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN    )
