import uuid
import os
import json
import unittest.mock as mock

from django.urls import reverse
from django.core.exceptions import ImproperlyConfigured
from rest_framework import status
from rest_framework.exceptions import ValidationError
from django.conf import settings


from api.models import Resource, Workspace
from resource_types import DATABASE_RESOURCE_TYPES
from api.tests.base import BaseAPITestCase
from api.tests import test_settings


class ResourceListTests(BaseAPITestCase):

    def setUp(self):

        self.url = reverse('resource-list')
        self.establish_clients()

    def test_list_resource_requires_auth(self):
        """
        Test that general requests to the endpoint generate 401
        """
        response = self.regular_client.get(self.url)
        self.assertTrue((response.status_code == status.HTTP_401_UNAUTHORIZED) 
        | (response.status_code == status.HTTP_403_FORBIDDEN))

    def test_admin_can_list_resource(self):
        """
        Test that admins can see all Resources.  Checks by comparing
        the pk (a UUID) between the database instances and those in the response.
        """
        response = self.authenticated_admin_client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        all_known_resource_uuids = set([str(x.pk) for x in Resource.objects.all()])
        received_resource_uuids = set([x['id'] for x in response.data])
        self.assertEqual(all_known_resource_uuids, received_resource_uuids)


    @mock.patch('api.views.resource_views.api_tasks')
    @mock.patch('api.views.resource_views.set_resource_to_inactive')
    def test_admin_can_create_resource(self, 
        mock_set_resource_to_inactive,
        mock_api_tasks):
        """
        Test that admins can create a Resource and that the proper validation
        methods are called.
        """
        # get all initial instances before anything happens:
        initial_resource_uuids = set([str(x.pk) for x in Resource.objects.all()])

        payload = {
            'owner_email': self.regular_user_1.email,
            'name': 'some_file.txt',
            'resource_type':'MTX'
        }
        response = self.authenticated_admin_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # get current instances:
        current_resource_uuids = set([str(x.pk) for x in Resource.objects.all()])
        difference_set = current_resource_uuids.difference(initial_resource_uuids)
        self.assertEqual(len(difference_set), 1)

        # check that the proper validation methods were called
        mock_set_resource_to_inactive.assert_called()
        mock_api_tasks.validate_resource.delay.assert_called()

        # check that the resource has the proper members set:
        r = Resource.objects.get(pk=list(difference_set)[0])
        self.assertFalse(r.is_active)
        # should be False since it was not explicitly set to True
        self.assertFalse(r.is_public)
        self.assertIsNone(r.resource_type)


    @mock.patch('api.serializers.resource.api_tasks')
    @mock.patch('api.serializers.resource.set_resource_to_inactive')
    def test_missing_owner_in_admin_resource_request_fails(self, 
        mock_set_resource_to_inactive,
        mock_api_tasks):
        """
        Test that admins must specify an owner_email field in their request
        to create a Resource directly via the API
        """
        # get all initial instances before anything happens:
        initial_resource_uuids = set([str(x.pk) for x in Resource.objects.all()])

        payload = {
            'name': 'some_file.txt',
            'resource_type':'MTX'
        }
        response = self.authenticated_admin_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        current_resource_uuids = set([str(x.pk) for x in Resource.objects.all()])
        difference_set = current_resource_uuids.difference(initial_resource_uuids)
        self.assertEqual(len(difference_set), 0)

    def test_bad_admin_request_fails(self):
        """
        Test that even admins must specify a valid resource_type.
        The type given below is junk.
        """
        # get all initial instances before anything happens:
        initial_resource_uuids = set([str(x.pk) for x in Resource.objects.all()])

        # payload is missing the resource_type key
        payload = {
            'owner_email': self.regular_user_1.email,
            'resource_type': 'ASDFADSFASDFASFSD',
            'name': 'some_file.txt',
        }
        response = self.authenticated_admin_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        current_resource_uuids = set([str(x.pk) for x in Resource.objects.all()])
        difference_set = current_resource_uuids.difference(initial_resource_uuids)
        self.assertEqual(len(difference_set), 0)

    def test_invalid_resource_type_raises_exception(self):
        """
        Test that a bad resource_type specification generates
        an error
        """
        payload = {
            'owner_email': self.regular_user_1.email,
            'name': 'some_file.txt',
            'resource_type': 'foo'
        }

        response = self.authenticated_admin_client.post(
            self.url, data=payload, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


    def test_null_resource_type_is_valid(self):
        """
        Test that an explicit null resource_type is OK.
        Users will eventually have to set their own type
        """
        # get all initial instances before anything happens:
        initial_resource_uuids = set([str(x.pk) for x in Resource.objects.all()])

        payload = {
            'owner_email': self.regular_user_1.email,
            'name': 'some_file.txt',
            'resource_type': None
        }

        response = self.authenticated_admin_client.post(
            self.url, data=payload, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # check that we have a new Resource in the database:
        current_resource_uuids = set([str(x.pk) for x in Resource.objects.all()])
        difference_set = current_resource_uuids.difference(initial_resource_uuids)
        self.assertEqual(len(difference_set), 1)

    def test_setting_workspace_ignored(self):
        """
        Since we can't directly assign a workspace on resource creation,
        requests containing workspaces should be fine,
        as the workspace key is ignored
        """

        # get the workspaces for user 2
        other_user_workspaces = Workspace.objects.filter(owner=self.regular_user_2)
        workspace = other_user_workspaces[0]

        payload = {
            'owner_email': self.regular_user_1.email,
            'name': 'some_file.txt',
            'resource_type': 'MTX',
            'workspaces': [workspace.pk,]
        }
        response = self.authenticated_admin_client.post(self.url, data=payload, format='json')
        j = response.json()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(j['workspaces'],[])


    def test_admin_sending_bad_email_raises_error(self):
        """
        Test that admins providing a bad email (a user who is not in the db) raises 400
        """
        # get all initial instances before anything happens:
        initial_resource_uuids = set([str(x.pk) for x in Resource.objects.all()])

        payload = {'owner_email': test_settings.JUNK_EMAIL,
            'name': 'some_file.txt',
            'resource_type': 'MTX'
        }
        response = self.authenticated_admin_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # get current instances to check none were created:
        current_resource_uuids = set([str(x.pk) for x in Resource.objects.all()])
        difference_set = current_resource_uuids.difference(initial_resource_uuids)
        self.assertEqual(len(difference_set), 0)

    def test_regular_user_post_raises_error(self):
        """
        Test that regular users cannot post to this endpoint (i.e. to
        create a Resource).  All Resource creation should be handled by
        the upload methods or be initiated by an admin.
        """
        payload = {'owner_email': self.regular_user_1.email,
            'name': 'some_file.txt',
            'resource_type': 'MTX'
        }
        response = self.authenticated_regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


    def test_users_can_list_resource(self):
        """
        Test that regular users can list ONLY their own resources
        """
        response = self.authenticated_regular_client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        all_known_resource_uuids = set([str(x.pk) for x in Resource.objects.all()])
        personal_resources = Resource.objects.filter(owner=self.regular_user_1)
        personal_resource_uuids = set([str(x.pk) for x in personal_resources])
        received_resource_uuids = set([x['id'] for x in response.data])

        # checks that the test below is not trivial.  i.e. there are Resources owned by OTHER users
        self.assertTrue(len(all_known_resource_uuids.difference(personal_resource_uuids)) > 0)

        # checks that they only get their own resources (by checking UUID)
        self.assertEqual(personal_resource_uuids, received_resource_uuids)



class ResourceDetailTests(BaseAPITestCase):

    def setUp(self):

        self.establish_clients()

        # get an example from the database:
        regular_user_resources = Resource.objects.filter(
            owner=self.regular_user_1,
        )
        if len(regular_user_resources) == 0:
            msg = '''
                Testing not setup correctly.  Please ensure that there is at least one
                Resource instance for the user {user}
            '''.format(user=self.regular_user_1)
            raise ImproperlyConfigured(msg)

        active_resources = []
        inactive_resources = []
        for r in regular_user_resources:
            if r.is_active:
                active_resources.append(r)
            else:
                inactive_resources.append(r)
        if len(active_resources) == 0:
            raise ImproperlyConfigured('Need at least one active resource.')
        if len(inactive_resources) == 0:
            raise ImproperlyConfigured('Need at least one INactive resource.')
        # grab the first:
        self.active_resource = active_resources[0]
        self.inactive_resource = inactive_resources[0]


        # we need some Resources that are associated with a Workspace and 
        # some that are not.
        unassociated_resources = []
        workspace_resources = []
        for r in regular_user_resources:
            workspace_set = r.workspaces.all()
            if (len(workspace_set) > 0) and (r.is_active):
                workspace_resources.append(r)
            elif r.is_active:
                unassociated_resources.append(r)
        
        # need an active AND unattached resource
        active_and_unattached = set(
                [x.pk for x in active_resources]
            ).intersection(set(
                [x.pk for x in unassociated_resources]
            )
        )
        if len(active_and_unattached) == 0:
            raise ImproperlyConfigured('Need at least one active and unattached'
                ' Resource to run this test.'
        )

        self.regular_user_unattached_resource = unassociated_resources[0]
        self.regular_user_workspace_resource = workspace_resources[0]
        self.populated_workspace = self.regular_user_workspace_resource.workspaces.all()[0]
        active_unattached_resource_pk = list(active_and_unattached)[0]
        self.regular_user_active_unattached_resource = Resource.objects.get(
            pk=active_unattached_resource_pk)

        self.url_for_unattached = reverse(
            'resource-detail', 
            kwargs={'pk':self.regular_user_unattached_resource.pk}
        )
        self.url_for_active_unattached = reverse(
            'resource-detail', 
            kwargs={'pk':self.regular_user_active_unattached_resource.pk}
        )
        self.url_for_workspace_resource = reverse(
            'resource-detail', 
            kwargs={'pk':self.regular_user_workspace_resource.pk}
        )
        self.url_for_active_resource = reverse(
            'resource-detail', 
            kwargs={'pk':self.active_resource.pk}
        )
        self.url_for_inactive_resource = reverse(
            'resource-detail', 
            kwargs={'pk':self.inactive_resource.pk}
        )

    def test_resource_detail_requires_auth(self):
        """
        Test that general requests to the endpoint generate 401
        """
        response = self.regular_client.get(self.url_for_unattached)
        self.assertTrue((response.status_code == status.HTTP_401_UNAUTHORIZED) 
        | (response.status_code == status.HTTP_403_FORBIDDEN))
        response = self.regular_client.get(self.url_for_workspace_resource)
        self.assertTrue((response.status_code == status.HTTP_401_UNAUTHORIZED) 
        | (response.status_code == status.HTTP_403_FORBIDDEN))

    def test_admin_can_view_resource_detail(self):
        """
        Test that admins can view the Workpace detail for anyone
        """
        response = self.authenticated_admin_client.get(self.url_for_unattached)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(str(self.regular_user_unattached_resource.pk), response.data['id'])

    @mock.patch('api.views.resource_views.api_tasks')
    def test_admin_can_delete_resource(self, mock_api_tasks):
        """
        Test that admin users can delete an unattached Resource
        """
        response = self.authenticated_admin_client.delete(self.url_for_active_unattached)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_api_tasks.delete_file.delay.assert_called()
        with self.assertRaises(Resource.DoesNotExist):
            Resource.objects.get(pk=self.regular_user_active_unattached_resource.pk)

    @mock.patch('api.views.resource_views.api_tasks')
    def test_admin_cannot_delete_workspace_resource(self, mock_api_tasks):
        """
        Test that even admin users can't delete a workspace-associated Resource if it 
        has not been used. This is the case whether or not operations were performed
        using that resource.
        """
        response = self.authenticated_admin_client.delete(self.url_for_workspace_resource)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        mock_api_tasks.delete_file.delay.assert_not_called()
        Resource.objects.get(pk=self.regular_user_workspace_resource.pk)

    def test_users_can_view_own_resource_detail(self):
        """
        Test that regular users can view their own Resource detail.
        """
        response = self.authenticated_regular_client.get(self.url_for_unattached)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(str(self.regular_user_unattached_resource.pk), response.data['id'])


    @mock.patch('api.views.resource_views.api_tasks')
    @mock.patch('api.views.resource_views.check_for_resource_operations')
    def test_users_cannot_delete_attached_resource(self, 
        mock_check_for_resource_operations,
        mock_api_tasks):
        """
        Test that regular users can't delete their own Resource even if it has 
        NOT been used within a Workspace. Users need to unattach it. Check that the 
        direct call to delete is rejected.
        """
        mock_check_for_resource_operations.return_value = False
        response = self.authenticated_regular_client.delete(self.url_for_workspace_resource)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        mock_api_tasks.delete_file.delay.assert_not_called()
        # check that the resource still exists
        Resource.objects.get(pk=self.regular_user_workspace_resource.pk)

    def test_other_users_cannot_delete_resource(self):
        """
        Test that another regular users can't delete someone else's Workpace.
        """
        response = self.authenticated_other_client.delete(self.url_for_unattached)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_other_user_cannot_view_resource_detail(self):
        """
        Test that another regular user can't view the Workpace detail.
        """
        response = self.authenticated_other_client.get(self.url_for_unattached)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


    def test_users_cannot_change_owner(self):
        '''
        Regular users cannot change the owner of a Resource.  That
        would amount to assigning a Resource to someone else- do not
        want that.
        '''
        payload = {'owner_email':self.regular_user_2.email}
        response = self.authenticated_regular_client.put(
            self.url_for_unattached, payload, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        payload = {'owner_email':self.regular_user_2.email}
        response = self.authenticated_regular_client.put(
            self.url_for_workspace_resource, payload, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_cannot_directly_edit_resource_workspace(self):
        '''
        Test that the put/patch to the resources endpoint 
        ignores any request to change teh workspace
        '''
        # get the workspace to which the resource is assigned:
        all_workspaces = self.regular_user_workspace_resource.workspaces.all()
        workspace1 = all_workspaces[0]

        # get another workspace owned by that user:
        all_user_workspaces = Workspace.objects.filter(
            owner=self.regular_user_workspace_resource.owner
        )
        other_workspaces = [x for x in all_user_workspaces if not x==workspace1]
        if len(other_workspaces) == 0:
            raise ImproperlyConfigured('Need to create another Workspace for'
                ' user {user_email}'.format(
                    user_email=self.regular_user_workspace_resource.owner.email
                )
            )
        other_workspace = other_workspaces[0]
        payload = {'workspace': other_workspace.pk}

        # try for a resource already attached to a workspace
        response = self.authenticated_regular_client.put(
            self.url_for_workspace_resource, payload, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


    def test_user_cannot_change_active_status(self):
        '''
        The `is_active` boolean cannot be altered by a regular user.
        `is_active` is used to block edits while validation is processing, etc.

        The `is_active` is ignored for requests from regular users
        so there is no 400 returned.  Rather, we check that the flag
        has not changed.
        ''' 
        # check that it was not active to start:
        self.assertTrue(self.regular_user_workspace_resource.is_active)
        payload = {'is_active': False}
        response = self.authenticated_regular_client.put(
            self.url_for_workspace_resource, payload, format='json'
        )
        r = Resource.objects.get(pk=self.regular_user_workspace_resource.pk)
        self.assertTrue(r.is_active)

    def test_admin_cannot_change_active_status(self):
        '''
        The `is_active` boolean cannot be reset via the API, even by
        an admin
        ''' 
        # find the status at the start:
        initial_status = self.regular_user_unattached_resource.is_active
        final_status = not initial_status

        payload = {'is_active': final_status}
        response = self.authenticated_admin_client.put(
            self.url_for_unattached, payload, format='json'
        )
        r = Resource.objects.get(pk=self.regular_user_unattached_resource.pk)

        # check that the bool changed:
        self.assertEqual(r.is_active, initial_status)


    def test_user_cannot_change_status_message(self):
        '''
        The `status` string canNOT be reset by a regular user
        ''' 
        # check that it was not active to start:
        orig_status = self.regular_user_unattached_resource.status

        payload = {'status': 'something'}
        response = self.authenticated_regular_client.put(
            self.url_for_unattached, payload, format='json'
        )
        r = Resource.objects.get(pk=self.regular_user_unattached_resource.pk)
        self.assertTrue(r.status == orig_status)

    def test_admin_can_change_status_message(self):
        '''
        The `status` string can be reset by an admin
        ''' 
        # check that it was not active to start:
        orig_status = self.active_resource.status

        payload = {'status': 'something'}
        response = self.authenticated_admin_client.put(
            self.url_for_active_resource, payload, format='json'
        )
        r = Resource.objects.get(pk=self.active_resource.pk)
        self.assertFalse(r.status == orig_status)

    def test_user_cannot_change_date_added(self):
        '''
        Once the Resource has been added, there is no editing
        of the DateTime.
        '''
        orig_datetime = self.regular_user_unattached_resource.creation_datetime
        original_pk = self.regular_user_unattached_resource.pk

        date_str = 'May 20, 2018 (16:00:07)'
        payload = {'created': date_str}
        response = self.authenticated_regular_client.put(
            self.url_for_unattached, payload, format='json'
        )
        # since the field is ignored, it will not raise any exception.
        # Still want to check that the object is unchanged:
        r = Resource.objects.get(pk=original_pk)
        self.assertEqual(orig_datetime, r.creation_datetime)
        orig_datestring = orig_datetime.strftime('%B %d, %Y, (%H:%M:%S)')
        self.assertTrue(orig_datestring != date_str)


    def test_user_can_make_resource_public(self):
        '''
        Make a Resource public so that others may
        see/use it.  Note that use by others creates a copy
        so that the original data remains the same.
        '''
        private_resources = Resource.objects.filter(
            owner = self.regular_user_1,
            is_active = True,
            is_public = False
        )
        if len(private_resources) > 0:
            private_resource = private_resources[0]

            url = reverse(
                'resource-detail', 
                kwargs={'pk':private_resource.pk}
            )
            payload = {'is_public': True}
            response = self.authenticated_regular_client.put(
                url, payload, format='json'
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            r = Resource.objects.get(pk=private_resource.pk)
            self.assertTrue(r.is_public)

        else:
            raise ImproperlyConfigured('To properly run this test, you'
            ' need to have at least one public Resource.')

    def test_user_can_make_resource_private(self):
        '''
        If a Resource was public, make it private.
        This will NOT "recall" datasets that were derived
        from this (e.g. if someone else used it while it was public)
        '''
        active_and_public_resources = Resource.objects.filter(
            is_active = True,
            is_public = True,
            owner = self.regular_user_1
        )
        if len(active_and_public_resources) == 0:
            raise ImproperlyConfigured('To properly run this test, you'
            ' need to have at least one public AND active Resource.')
        r = active_and_public_resources[0]
        url = reverse(
            'resource-detail', 
            kwargs={'pk':r.pk}
        )
        payload = {'is_public': False}
        response = self.authenticated_regular_client.put(
            url, payload, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        updated_resource = Resource.objects.get(pk=r.pk)
        self.assertFalse(updated_resource.is_public)



    def test_cannot_make_changes_when_inactive(self):
        '''
        Test that no changes can be made when the resource is inactive.
        '''
        self.assertFalse(self.inactive_resource.is_active)

        # just try to change the path as an example
        payload = {'path': '/some/path/to/file.txt'}
        response = self.authenticated_admin_client.put(
            self.url_for_inactive_resource, payload, format='json'
        )
        self.assertTrue(response.status_code == status.HTTP_400_BAD_REQUEST)

    def test_admin_can_change_path(self):
        '''
        Path is only relevant for internal/database use so 
        users cannot change that. Admins may, however
        '''
        self.assertTrue(self.active_resource.is_active)
        original_path = self.active_resource.path
        new_path = '/some/new/path.txt'
        payload = {'path': new_path}
        response = self.authenticated_admin_client.put(
            self.url_for_active_resource, payload, format='json'
        )
        # query db for that same Resource object and verify that the path
        # has not been changed:
        obj = Resource.objects.get(pk=self.active_resource.pk)
        self.assertEqual(obj.path, new_path)
        self.assertFalse(obj.path == original_path)

    def test_user_cannot_change_path(self):
        '''
        Path is only relevant for internal/database use so 
        users cannot change that.
        '''
        original_path = self.regular_user_unattached_resource.path
        payload = {'path': '/some/new/path.txt'}
        response = self.authenticated_regular_client.put(
            self.url_for_unattached, payload, format='json'
        )
        # query db for that same Resource object and verify that the path
        # has not been changed:
        obj = Resource.objects.get(pk=self.regular_user_unattached_resource.pk)
        self.assertEqual(obj.path, original_path)


    def test_user_can_change_resource_name(self):
        '''
        Users may change the Resource name.  This does NOT
        change anything about the path, etc.
        '''
        original_name = self.active_resource.name

        payload = {'name': 'newname.txt'}
        response = self.authenticated_regular_client.put(
            self.url_for_active_resource, payload, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        json_obj = response.json()
        self.assertTrue(json_obj['name'], 'newname.txt')

        # just double check that the original name wasn't the same
        # by chance
        self.assertTrue(original_name != 'newname.txt')

    @mock.patch('api.serializers.resource.api_tasks')
    def test_changing_resource_type_resets_status(self,  
        mock_api_tasks):
        '''
        If an attempt is made to change the resource type
        ensure that the resource has its "active" state 
        set to False and that the status changes.

        Since the validation can take some time, it will call
        the asynchronous validation process.
        '''
        current_resource_type = self.active_resource.resource_type
        other_types = set(
            [x[0] for x in DATABASE_RESOURCE_TYPES]
            ).difference(set([current_resource_type]))
        newtype = list(other_types)[0]

        # verify that we are actually changing the type 
        # in this request (i.e. not a trivial test)
        self.assertFalse(
            newtype == current_resource_type
        )
        payload = {'resource_type': newtype}
        response = self.authenticated_regular_client.put(
            self.url_for_active_resource, payload, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        r = Resource.objects.get(pk=self.active_resource.pk)

        # active state set to False
        self.assertFalse(r.is_active)

        # check that the validation method was called.
        mock_api_tasks.validate_resource.delay.assert_called_with(self.active_resource.pk, newtype)


    def test_setting_workspace_to_null_fails(self):
        '''
        Test that directly setting the workspace to null fails.
        Users can't change a Resource's workspace.  They can only 
        remove unused Resources from a Workspace.
        '''
        payload = {'workspace': None}

        # get the original set of workspaces for the resource
        orig_workspaces = [x.pk for x in self.regular_user_workspace_resource.workspaces.all()]

        # try for an attached resource
        response = self.authenticated_regular_client.put(
            self.url_for_workspace_resource, payload, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # query the resource again, see that the workspaces have not 
        # changed
        rr = Resource.objects.get(pk=self.regular_user_workspace_resource.pk)
        current_workspaces = [x.pk for x in rr.workspaces.all()]
        self.assertEqual(current_workspaces, orig_workspaces)

        # try for an unattached resource
        # get the original set of workspaces for the resource
        orig_workspaces = [x.pk for x in self.regular_user_unattached_resource.workspaces.all()]

        response = self.authenticated_regular_client.put(
            self.url_for_unattached, payload, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # query the resource again, see that the workspaces have not 
        # changed
        rr = Resource.objects.get(pk=self.regular_user_unattached_resource.pk)
        current_workspaces = [x.pk for x in rr.workspaces.all()]
        self.assertEqual(current_workspaces, orig_workspaces)

class ResourceContentTests(BaseAPITestCase):
    '''
    Tests the endpoint which returns the file contents in full
    '''
    def setUp(self):

        self.establish_clients()
        self.TESTDIR = os.path.join(
            os.path.dirname(__file__),
            'resource_contents_test_files'    
        )
        # get an example from the database:
        regular_user_resources = Resource.objects.filter(
            owner=self.regular_user_1,
        )
        if len(regular_user_resources) == 0:
            msg = '''
                Testing not setup correctly.  Please ensure that there is at least one
                Resource instance for the user {user}
            '''.format(user=self.regular_user_1)
            raise ImproperlyConfigured(msg)
        for r in regular_user_resources:
            if r.is_active:
                active_resource = r
                break
        self.resource = active_resource
        self.url = reverse(
            'resource-contents', 
            kwargs={'pk':self.resource.pk}
        )
        for r in regular_user_resources:
            if not r.is_active:
                inactive_resource = r
                break
        self.inactive_resource_url = reverse(
            'resource-contents', 
            kwargs={'pk':inactive_resource.pk}
        )

    @mock.patch('api.utilities.resource_utilities.get_storage_backend')
    def test_page_param_ignored_for_non_paginated_resource(self, mock_get_storage_backend):
        '''
        Certain resource types (e.g. JSON) don't have straightforward
        pagination schemes. If the JSON was a list, fine...but generally
        that's not the case.

        Check that any page params supplied are ignored and the entire
        resource is returned
        '''
        f = os.path.join(self.TESTDIR, 'json_file.json')
        self.resource.path = f
        self.resource.resource_type = 'JSON'
        self.resource.save()
        mock_storage_backend = mock.MagicMock()
        mock_storage_backend.get_local_resource_path.return_value = f
        mock_get_storage_backend.return_value = mock_storage_backend

        # check that full file works without query params
        base_url = reverse(
            'resource-contents', 
            kwargs={'pk':self.resource.pk}
        )
        response = self.authenticated_regular_client.get(
            base_url, format='json'
        )
        self.assertEqual(response.status_code, 
            status.HTTP_200_OK)
        results = response.json()
        file_contents = json.load(open(f))
        self.assertDictEqual(results, file_contents)

        # add the query params onto the end of the url.
        # See that it still works (i.e. query params are ignored)
        url = base_url + '?page=1'
        response = self.authenticated_regular_client.get(
            url, format='json'
        )
        j = response.json()
        self.assertDictEqual(results, file_contents)


    @mock.patch('api.utilities.resource_utilities.get_storage_backend')
    def test_response_with_na_and_inf(self, mock_get_storage_backend):
        '''
        Tests the case where the requested resource has infinities and NA's
        '''
        f = os.path.join(self.TESTDIR, 'demo_file1.tsv')
        self.resource.path = f
        self.resource.save()
        mock_storage_backend = mock.MagicMock()
        mock_storage_backend.get_local_resource_path.return_value = f
        mock_get_storage_backend.return_value = mock_storage_backend
        response = self.authenticated_regular_client.get(
            self.url, format='json'
        )
        j = response.json()

        # the second row (index=1) has a negative infinity.
        self.assertTrue(j[1]['values']['log2FoldChange'] == settings.NEGATIVE_INF_MARKER)

        # the third row (index=2) has a positive infinity.
        self.assertTrue(j[2]['values']['log2FoldChange'] == settings.POSITIVE_INF_MARKER)
        
        # the third row has a padj of NaN, which gets converted to None 
        self.assertIsNone(j[2]['values']['padj'])

    def test_content_request_from_non_owner(self):
        '''
        Tests where content is requested from someone else's
        resource
        '''
        response = self.authenticated_other_client.get(
            self.url, format='json'
        )
        self.assertEqual(response.status_code, 
            status.HTTP_403_FORBIDDEN)

    def test_content_request_for_inactive_fails(self):
        '''
        Tests where content is requested for a resource
        that is inactive.
        '''
        response = self.authenticated_regular_client.get(
            self.inactive_resource_url, format='json'
        )
        self.assertEqual(response.status_code, 
            status.HTTP_400_BAD_REQUEST)


    @mock.patch('api.views.resource_views.ResourceContents.check_request_validity')
    @mock.patch('api.views.resource_views.get_resource_view')
    def test_error_reported(self, mock_view, mock_check_request_validity):
        '''
        If there was some error in preparing the preview, 
        the returned data will have an 'error' key
        '''
        mock_check_request_validity.return_value = self.resource
        mock_view.side_effect = Exception('something bad happened!')
        response = self.authenticated_regular_client.get(
            self.url, format='json'
        )
        self.assertEqual(response.status_code, 
            status.HTTP_500_INTERNAL_SERVER_ERROR)   

        self.assertTrue('error' in response.json())     

    @mock.patch('api.views.resource_views.ResourceContents.check_request_validity')
    @mock.patch('api.utilities.resource_utilities.get_storage_backend')
    def test_expected_response(self, mock_get_storage_backend, mock_check_request_validity):
        '''
        Test 
        '''
        f = os.path.join(self.TESTDIR, 'demo_file2.tsv')
        self.resource.path = f
        self.resource.save()
        mock_check_request_validity.return_value = self.resource
        mock_storage_backend = mock.MagicMock()
        mock_storage_backend.get_local_resource_path.return_value = f
        mock_get_storage_backend.return_value = mock_storage_backend
        response = self.authenticated_regular_client.get(
            self.url, format='json'
        )
        self.assertEqual(response.status_code, 
            status.HTTP_200_OK)
        j = response.json()

        expected_return = [
            {
                "rowname": "gA",
                "values": {
                "colA": 0,
                "colB": 1,
                "colC": 2
                }
            },
            {
                "rowname": "gB",
                "values": {
                "colA": 10,
                "colB": 11,
                "colC": 12
                }
            },
            {
                "rowname": "gC",
                "values": {
                "colA": 20,
                "colB": 21,
                "colC": 22
                }
            }
        ]
        self.assertEqual(expected_return, j) 

    @mock.patch('api.views.resource_views.ResourceContents.check_request_validity')
    @mock.patch('api.utilities.resource_utilities.get_storage_backend')
    def test_resource_contents_pagination(self, mock_get_storage_backend, mock_check_request_validity):
        f = os.path.join(self.TESTDIR, 'demo_table_for_pagination.tsv')
        N = 155 # the number of records in our demo file

        # just a double-check to ensure the test data is large enough
        # for the pagination to be general
        self.assertTrue(N > settings.REST_FRAMEWORK['PAGE_SIZE'])
        self.resource.path = f
        self.resource.save()
        mock_check_request_validity.return_value = self.resource
        mock_storage_backend = mock.MagicMock()
        mock_storage_backend.get_local_resource_path.return_value = f
        mock_get_storage_backend.return_value = mock_storage_backend

        # the base url (no query params) should return all the records
        base_url = reverse(
            'resource-contents', 
            kwargs={'pk':self.resource.pk}
        )
        response = self.authenticated_regular_client.get(
            base_url, format='json'
        )
        self.assertEqual(response.status_code, 
            status.HTTP_200_OK)
        results = response.json()
        self.assertTrue(len(results) == N)
        first_record = results[0]
        final_record = results[-1]
        self.assertTrue(first_record['rowname'] == 'g0')
        self.assertTrue(final_record['rowname'] == 'g154')

        # add the query params onto the end of the url:
        url = base_url + '?page=1'
        response = self.authenticated_regular_client.get(
            url, format='json'
        )
        self.assertEqual(response.status_code, 
            status.HTTP_200_OK)
        j = response.json()
        results = j['results']
        self.assertTrue(len(results) == settings.REST_FRAMEWORK['PAGE_SIZE'])
        first_record = results[0]
        final_record = results[-1]
        self.assertTrue(first_record['rowname'] == 'g0')
        self.assertTrue(final_record['rowname'] == 'g49')

        # add the query params onto the end of the url:
        url = base_url + '?page=2'
        response = self.authenticated_regular_client.get(
            url, format='json'
        )
        self.assertEqual(response.status_code, 
            status.HTTP_200_OK)
        j = response.json()
        results = j['results']
        self.assertTrue(len(results) == settings.REST_FRAMEWORK['PAGE_SIZE'])
        first_record = results[0]
        final_record = results[-1]
        self.assertTrue(first_record['rowname'] == 'g50')
        self.assertTrue(final_record['rowname'] == 'g99')

        # add the query params onto the end of the url:
        url = base_url + '?page=last'
        response = self.authenticated_regular_client.get(
            url, format='json'
        )
        self.assertEqual(response.status_code, 
            status.HTTP_200_OK)
        j = response.json()
        results = j['results']
        leftover_size = N % settings.REST_FRAMEWORK['PAGE_SIZE']
        self.assertTrue(len(results) == leftover_size)
        first_record = results[0]
        final_record = results[-1]
        self.assertTrue(first_record['rowname'] == 'g150')
        self.assertTrue(final_record['rowname'] == 'g154')

        # by itself the page_size param doesn't do anything.
        # It needs the page param
        page_size = 20
        suffix = '?page_size=%d' % page_size
        url = base_url + suffix
        response = self.authenticated_regular_client.get(
            url, format='json'
        )
        self.assertEqual(response.status_code, 
            status.HTTP_200_OK)
        results = response.json()
        self.assertTrue(len(results) == N)
        first_record = results[0]
        final_record = results[-1]
        self.assertTrue(first_record['rowname'] == 'g0')
        self.assertTrue(final_record['rowname'] == 'g154')

        # test the page_size param:
        page_size = 20
        suffix = '?page_size=%d&page=2' % page_size
        url = base_url + suffix
        response = self.authenticated_regular_client.get(
            url, format='json'
        )
        self.assertEqual(response.status_code, 
            status.HTTP_200_OK)
        j = response.json()
        results = j['results']
        self.assertTrue(len(results) == page_size)
        first_record = results[0]
        final_record = results[-1]
        self.assertTrue(first_record['rowname'] == 'g20')
        self.assertTrue(final_record['rowname'] == 'g39')

    @mock.patch('api.views.resource_views.ResourceContents.check_request_validity')
    @mock.patch('api.utilities.resource_utilities.get_storage_backend')
    def test_resource_contents_table_filter(self, mock_get_storage_backend, mock_check_request_validity):
        '''
        For testing if table-based resources are filtered correctly
        '''
        f = os.path.join(self.TESTDIR, 'demo_deseq_table.tsv')
        N = 39 # the number of rows in the table
        self.resource.path = f
        self.resource.save()
        mock_check_request_validity.return_value = self.resource
        mock_storage_backend = mock.MagicMock()
        mock_storage_backend.get_local_resource_path.return_value = f
        mock_get_storage_backend.return_value = mock_storage_backend
        
        # the base url (no query params) should return all the records
        base_url = reverse(
            'resource-contents', 
            kwargs={'pk':self.resource.pk}
        )
        response = self.authenticated_regular_client.get(
            base_url, format='json'
        )
        self.assertEqual(response.status_code, 
            status.HTTP_200_OK)
        results = response.json()
        self.assertTrue(len(results) == N)

        suffix = '?pvalue=[lte]:0.4'
        url = base_url + suffix
        response = self.authenticated_regular_client.get(
            url, format='json'
        )
        self.assertEqual(response.status_code, 
            status.HTTP_200_OK)
        results = response.json()
        self.assertTrue(len(results) == 2)
        returned_set = set([x['rowname'] for x in results])
        self.assertEqual({'HNRNPUL2', 'MAP1A'}, returned_set)

        # an empty result set
        suffix = '?pvalue=[lte]:0.004'
        url = base_url + suffix
        response = self.authenticated_regular_client.get(
            url, format='json'
        )
        self.assertEqual(response.status_code, 
            status.HTTP_200_OK)
        results = response.json()
        self.assertTrue(len(results) == 0)

        suffix = '?pvalue=[lte]:0.4&log2FoldChange=[gt]:0'
        url = base_url + suffix
        response = self.authenticated_regular_client.get(
            url, format='json'
        )
        self.assertEqual(response.status_code, 
            status.HTTP_200_OK)
        results = response.json()
        self.assertTrue(len(results) == 1)
        returned_set = set([x['rowname'] for x in results])
        self.assertEqual({'HNRNPUL2'}, returned_set)

        # note the missing delimiter, which makes the suffix invalid. Should return 400
        suffix = '?pvalue=[lte]:0.4&log2FoldChange=[gt]0'
        url = base_url + suffix
        response = self.authenticated_regular_client.get(
            url, format='json'
        )
        self.assertEqual(response.status_code, 
            status.HTTP_400_BAD_REQUEST)
        results = response.json()
        self.assertTrue('error' in results)

        # note the value ("a") can't be parsed as a number
        suffix = '?pvalue=[lte]:a'
        url = base_url + suffix
        response = self.authenticated_regular_client.get(
            url, format='json'
        )
        self.assertEqual(response.status_code, 
            status.HTTP_400_BAD_REQUEST)
        results = response.json()
        self.assertTrue('error' in results)

        # filter on a column that does not exist
        suffix = '?xyz=[lte]:0'
        url = base_url + suffix
        response = self.authenticated_regular_client.get(
            url, format='json'
        )
        self.assertEqual(response.status_code, 
            status.HTTP_400_BAD_REQUEST)
        results = response.json()
        self.assertTrue('error' in results)
        expected_error = (
            'There was a problem when parsing the request:'
            ' The column "xyz" is not available for filtering.'
        )
        self.assertEqual(results['error'], expected_error)

       # filter on a column that does not exist, but also including a valid field
        suffix = '?pvalue=[lte]:0.1&abc=[lte]:0'
        url = base_url + suffix
        response = self.authenticated_regular_client.get(
            url, format='json'
        )
        self.assertEqual(response.status_code, 
            status.HTTP_400_BAD_REQUEST)
        results = response.json()
        self.assertTrue('error' in results)
        expected_error = (
            'There was a problem when parsing the request:'
            ' The column "abc" is not available for filtering.'
        )
        self.assertEqual(results['error'], expected_error)


    @mock.patch('api.views.resource_views.ResourceContents.check_request_validity')
    @mock.patch('api.utilities.resource_utilities.get_storage_backend')
    def test_resource_contents_abs_val_table_filter(self, mock_get_storage_backend, mock_check_request_validity):
        '''
        For testing if table-based resources are filtered correctly using the absolute value filters
        '''
        f = os.path.join(self.TESTDIR, 'demo_deseq_table.tsv')
        N = 39 # the number of rows in the table
        self.resource.path = f
        self.resource.save()
        mock_check_request_validity.return_value = self.resource
        mock_storage_backend = mock.MagicMock()
        mock_storage_backend.get_local_resource_path.return_value = f
        mock_get_storage_backend.return_value = mock_storage_backend

        # the base url (no query params) should return all the records
        base_url = reverse(
            'resource-contents', 
            kwargs={'pk':self.resource.pk}
        )
        response = self.authenticated_regular_client.get(
            base_url, format='json'
        )
        self.assertEqual(response.status_code, 
            status.HTTP_200_OK)
        results = response.json()
        self.assertTrue(len(results) == N)

        suffix = '?log2FoldChange=[absgt]:2.0'
        url = base_url + suffix
        response = self.authenticated_regular_client.get(
            url, format='json'
        )
        self.assertEqual(response.status_code, 
            status.HTTP_200_OK)
        results = response.json()
        self.assertTrue(len(results) == 5)
        returned_set = set([x['rowname'] for x in results])
        self.assertEqual({'KRT18P27', 'PWWP2AP1', 'AMBP', 'ADH5P2', 'MMGT1'}, returned_set)

        suffix = '?log2FoldChange=[absgt]:2.0&pvalue=[lt]:0.5'
        url = base_url + suffix
        response = self.authenticated_regular_client.get(
            url, format='json'
        )
        self.assertEqual(response.status_code, 
            status.HTTP_200_OK)
        results = response.json()
        self.assertTrue(len(results) == 1)
        returned_set = set([x['rowname'] for x in results])
        self.assertEqual({'AMBP'}, returned_set)


    @mock.patch('api.views.resource_views.ResourceContents.check_request_validity')
    @mock.patch('api.utilities.resource_utilities.get_storage_backend')
    def test_table_filter_with_string(self, mock_get_storage_backend, mock_check_request_validity):
        '''
        For testing if table-based resources are filtered correctly on string fields
        '''
        f = os.path.join(self.TESTDIR, 'table_with_string_field.tsv')
        N = 3 # the number of rows in the table
        self.resource.path = f
        self.resource.save()
        mock_check_request_validity.return_value = self.resource
        mock_storage_backend = mock.MagicMock()
        mock_storage_backend.get_local_resource_path.return_value = f
        mock_get_storage_backend.return_value = mock_storage_backend

        # the base url (no query params) should return all the records
        base_url = reverse(
            'resource-contents', 
            kwargs={'pk':self.resource.pk}
        )
        response = self.authenticated_regular_client.get(
            base_url, format='json'
        )
        self.assertEqual(response.status_code, 
            status.HTTP_200_OK)
        results = response.json()
        self.assertTrue(len(results) == N)

        suffix = '?colB=abc'
        url = base_url + suffix
        response = self.authenticated_regular_client.get(
            url, format='json'
        )
        self.assertEqual(response.status_code, 
            status.HTTP_200_OK)
        results = response.json()
        self.assertTrue(len(results) == 2)
        returned_set = set([x['rowname'] for x in results])
        self.assertEqual({'A', 'C'}, returned_set)

        suffix = '?colB=abc&colA=[lt]:0.02'
        url = base_url + suffix
        response = self.authenticated_regular_client.get(
            url, format='json'
        )
        self.assertEqual(response.status_code, 
            status.HTTP_200_OK)
        results = response.json()
        self.assertTrue(len(results) == 1)
        returned_set = set([x['rowname'] for x in results])
        self.assertEqual({'A'}, returned_set)

        # filter which gives zero results
        suffix = '?colB=aaa'
        url = base_url + suffix
        response = self.authenticated_regular_client.get(
            url, format='json'
        )
        self.assertEqual(response.status_code, 
            status.HTTP_200_OK)
        results = response.json()
        self.assertTrue(len(results) == 0)

    @mock.patch('api.views.resource_views.ResourceContents.check_request_validity')
    @mock.patch('api.utilities.resource_utilities.get_storage_backend')
    def test_resource_contents_sort(self, mock_get_storage_backend, mock_check_request_validity):
        '''
        For testing if table-based resources are sorted correctly
        '''
        f = os.path.join(self.TESTDIR, 'demo_deseq_table.tsv')
        N = 39 # the number of rows in the table
        self.resource.path = f
        self.resource.save()
        mock_check_request_validity.return_value = self.resource
        mock_storage_backend = mock.MagicMock()
        mock_storage_backend.get_local_resource_path.return_value = f
        mock_get_storage_backend.return_value = mock_storage_backend

        # the base url (no query params) should return all the records
        base_url = reverse(
            'resource-contents', 
            kwargs={'pk':self.resource.pk}
        )
        response = self.authenticated_regular_client.get(
            base_url, format='json'
        )
        self.assertEqual(response.status_code, 
            status.HTTP_200_OK)
        results = response.json()
        self.assertTrue(len(results) == N)

        suffix = '?{s}={a}:padj,{d}:log2FoldChange'.format(
            s = settings.SORT_PARAM,
            a = settings.ASCENDING,
            d = settings.DESCENDING
        )
        url = base_url + suffix
        response = self.authenticated_regular_client.get(
            url, format='json'
        )
        self.assertEqual(response.status_code, 
            status.HTTP_200_OK)
        results = response.json()
        gene_ordering = [x['rowname'] for x in results]
        expected_ordering = [
            'AC011841.4', 
            'UNCX', 
            'KRT18P27', 
            'ECHS1', 
            'ADH5P2', 
            'OR2L8', 
            'RN7SL99P', 
            'KRT18P19', 
            'CTD-2532D12.5', 
            'HNRNPUL2', 
            'TFAMP1', 
            'MAP1A', 
            'AC000123.4', 
            'HTR7P1', 
            'PWWP2AP1', 
            'AMBP', 
            'MMGT1'
        ]
        # only compare the first few. After that, the sorting is arbitrary as there
        # are na's, etc.
        self.assertEqual(
            gene_ordering[:len(expected_ordering)], 
            expected_ordering
        )

        # flip the order of the log2FoldChange:
        suffix = '?{s}={a}:padj,{a}:log2FoldChange'.format(
            s = settings.SORT_PARAM,
            a = settings.ASCENDING
        )
        url = base_url + suffix
        response = self.authenticated_regular_client.get(
            url, format='json'
        )
        self.assertEqual(response.status_code, 
            status.HTTP_200_OK)
        results = response.json()
        gene_ordering = [x['rowname'] for x in results]
        # the first few are unambiguous, as the padj are different
        # the later ones have the same padj, but different log2FoldChange
        # We include some +/-inf values also.
        expected_ordering = [
            'UNCX', 
            'AC011841.4', 
            'KRT18P27', 
            'ECHS1', 
            'MMGT1',
            'AMBP',
            'PWWP2AP1',
            'HTR7P1',
            'AC000123.4',
            'MAP1A',
            'TFAMP1',
            'HNRNPUL2',
            'CTD-2532D12.5',
            'KRT18P19',
            'RN7SL99P',
            'OR2L8',
            'ADH5P2'
        ]
        # only compare the first few. After that, the sorting is arbitrary as there
        # are na's, etc.
        self.assertEqual(
            gene_ordering[:len(expected_ordering)], 
            expected_ordering
        )

    @mock.patch('api.views.resource_views.ResourceContents.check_request_validity')
    @mock.patch('api.utilities.resource_utilities.get_storage_backend')
    def test_resource_contents_sort_and_filter(self, mock_get_storage_backend, mock_check_request_validity):
        '''
        For testing if table-based resources are sorted correctly when used
        with filters.
        '''
        f = os.path.join(self.TESTDIR, 'demo_deseq_table.tsv')
        N = 39 # the number of rows in the table
        self.resource.path = f
        self.resource.save()
        mock_check_request_validity.return_value = self.resource
        mock_storage_backend = mock.MagicMock()
        mock_storage_backend.get_local_resource_path.return_value = f
        mock_get_storage_backend.return_value = mock_storage_backend

        # the base url (no query params) should return all the records
        base_url = reverse(
            'resource-contents', 
            kwargs={'pk':self.resource.pk}
        )
        response = self.authenticated_regular_client.get(
            base_url, format='json'
        )
        self.assertEqual(response.status_code, 
            status.HTTP_200_OK)
        results = response.json()
        self.assertTrue(len(results) == N)

        suffix = '?padj=[lt]:0.3&{s}={a}:padj,{d}:log2FoldChange'.format(
            s = settings.SORT_PARAM,
            a = settings.ASCENDING,
            d = settings.DESCENDING
        )
        url = base_url + suffix
        response = self.authenticated_regular_client.get(
            url, format='json'
        )
        self.assertEqual(response.status_code, 
            status.HTTP_200_OK)
        results = response.json()
        self.assertTrue(len(results) == 2)
        gene_ordering = [x['rowname'] for x in results]
        expected_ordering = [
            'AC011841.4', 
            'UNCX'
        ] 
        # only compare the first few. After that, the sorting is arbitrary as there
        # are na's, etc.
        self.assertEqual(
            gene_ordering, 
            expected_ordering
        )

    @mock.patch('api.views.resource_views.ResourceContents.check_request_validity')
    @mock.patch('api.utilities.resource_utilities.get_storage_backend')
    def test_malformatted_sort_and_filter(self, mock_get_storage_backend, mock_check_request_validity):
        '''
        For testing that bad request params are handled well.
        '''
        f = os.path.join(self.TESTDIR, 'demo_deseq_table.tsv')
        N = 39 # the number of rows in the table
        self.resource.path = f
        self.resource.save()
        mock_check_request_validity.return_value = self.resource
        mock_storage_backend = mock.MagicMock()
        mock_storage_backend.get_local_resource_path.return_value = f
        mock_get_storage_backend.return_value = mock_storage_backend

        # the base url (no query params) should return all the records
        base_url = reverse(
            'resource-contents', 
            kwargs={'pk':self.resource.pk}
        )
        response = self.authenticated_regular_client.get(
            base_url, format='json'
        )
        self.assertEqual(response.status_code, 
            status.HTTP_200_OK)
        results = response.json()
        self.assertTrue(len(results) == N)

        bad_sort_kw = 'sort'
        self.assertFalse(bad_sort_kw == settings.SORT_PARAM) # to ensure that it's indeed a "bad" param
        suffix = '?{s}={a}:padj,{d}:log2FoldChange'.format(
            s = bad_sort_kw,
            a = settings.ASCENDING,
            d = settings.DESCENDING
        )
        url = base_url + suffix
        response = self.authenticated_regular_client.get(
            url, format='json'
        )

        self.assertEqual(response.status_code, 
            status.HTTP_400_BAD_REQUEST)
        results = response.json()
        self.assertTrue('error' in results)
        expected_error = (
            'There was a problem when parsing the request:'
            ' The column "{b}" is not available for filtering.'.format(b=bad_sort_kw)
        )
        self.assertEqual(results['error'], expected_error)

        bad_asc_param = 'aaa'
        self.assertFalse(bad_asc_param == settings.ASCENDING)
        suffix = '?{s}={a}:padj,{d}:log2FoldChange'.format(
            s = settings.SORT_PARAM,
            a = bad_asc_param,
            d = settings.DESCENDING
        )
        url = base_url + suffix
        response = self.authenticated_regular_client.get(
            url, format='json'
        )

        self.assertEqual(response.status_code, 
            status.HTTP_400_BAD_REQUEST)
        results = response.json()
        self.assertTrue('error' in results)
        expected_error = (
            'There was a problem when parsing the request: '
            'The sort order "{b}" is not an available option. Choose from: {a},{d}'.format(
                b = bad_asc_param,
                a = settings.ASCENDING,
                d = settings.DESCENDING  
            )
        )
        self.assertEqual(results['error'], expected_error)

        # bad column (should be padj, not adjP)
        suffix = '?{s}={a}:adjP,{d}:log2FoldChange'.format(
            s = settings.SORT_PARAM,
            a = settings.ASCENDING,
            d = settings.DESCENDING
        )
        url = base_url + suffix
        response = self.authenticated_regular_client.get(
            url, format='json'
        )
        self.assertEqual(response.status_code, 
            status.HTTP_400_BAD_REQUEST)
        results = response.json()
        expected_error = (
            'There was a problem when parsing the request:'
            ' The column identifier "adjP" does not exist in this resource.'
            ' Options are: overall_mean,Control,Experimental,log2FoldChange,lfcSE,stat,pvalue,padj'
        )
        self.assertEqual(results['error'], expected_error)

    @mock.patch('api.views.resource_views.ResourceContents.check_request_validity')
    @mock.patch('api.utilities.resource_utilities.get_storage_backend')
    def test_sort_on_string_field(self, mock_get_storage_backend, mock_check_request_validity):
        '''
        For testing if table-based resources are sorted correctly when
        sorting on a non-numeric/string field
        '''
        f = os.path.join(self.TESTDIR, 'table_with_string_field.tsv')
        N = 3 # the number of rows in the table
        self.resource.path = f
        self.resource.save()
        mock_check_request_validity.return_value = self.resource
        mock_storage_backend = mock.MagicMock()
        mock_storage_backend.get_local_resource_path.return_value = f
        mock_get_storage_backend.return_value = mock_storage_backend

        # the base url (no query params) should return all the records
        base_url = reverse(
            'resource-contents', 
            kwargs={'pk':self.resource.pk}
        )
        response = self.authenticated_regular_client.get(
            base_url, format='json'
        )
        self.assertEqual(response.status_code, 
            status.HTTP_200_OK)
        results = response.json()
        self.assertTrue(len(results) == N)

        suffix = '?{s}={a}:colB,{d}:colA'.format(
            s = settings.SORT_PARAM,
            a = settings.ASCENDING,
            d = settings.DESCENDING
        )
        url = base_url + suffix
        response = self.authenticated_regular_client.get(
            url, format='json'
        )
        self.assertEqual(response.status_code, 
            status.HTTP_200_OK)
        results = response.json()
        expected_ordering = ['C', 'A', 'B']
        self.assertEqual([x['rowname'] for x in results], expected_ordering)

        suffix = '?{s}={a}:colB,{a}:colA'.format(
            s = settings.SORT_PARAM,
            a = settings.ASCENDING
        )
        url = base_url + suffix
        response = self.authenticated_regular_client.get(
            url, format='json'
        )
        self.assertEqual(response.status_code, 
            status.HTTP_200_OK)
        results = response.json()
        expected_ordering = ['A', 'C', 'B']
        self.assertEqual([x['rowname'] for x in results], expected_ordering)