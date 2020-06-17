import unittest.mock as mock

from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from rest_framework import status

from api.tests.base import BaseAPITestCase
from api.tests import test_settings

User = get_user_model()

class UserListTests(BaseAPITestCase):

    def setUp(self):

        self.url = reverse('user-list')
        self.establish_clients()

    def test_list_users_requires_auth(self):
        """
        Test that general requests to the endpoint generate 401
        """
        response = self.regular_client.get(self.url)
        self.assertTrue((response.status_code == status.HTTP_401_UNAUTHORIZED) 
        | (response.status_code == status.HTTP_403_FORBIDDEN))

    def test_admin_can_list_user(self):
        """
        Test that admins can see all Users.  Checks by comparing
        the pk between the database instances and those in the response.
        """
        response = self.authenticated_admin_client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        all_known_user_emails = set([str(x.email) for x in User.objects.all()])
        received_user_emails = set([x['email'] for x in response.data])
        self.assertEqual(all_known_user_emails, received_user_emails)

    def test_admin_can_create_user(self):
        """
        Test that admins can create a User
        """
        # get all initial instances before anything happens:
        initial_users = set([str(x.pk) for x in User.objects.all()])

        payload = {'email': 'new_email@foo.com', 'password': 'abc123!'}
        response = self.authenticated_admin_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # get current instances:
        current_users = set([str(x.pk) for x in User.objects.all()])
        difference_set = current_users.difference(initial_users)
        self.assertEqual(len(difference_set), 1)

    def test_regular_user_cannot_list(self):
        """
        Test that regular users can't list users
        """
        response = self.authenticated_regular_client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_regular_user_cannot_create_user(self):
        """
        Test that regular users can't create new users
        """
        # get all initial instances before anything happens:
        initial_users = set([str(x.pk) for x in User.objects.all()])

        payload = {'email': 'new_email@foo.com', 'password': 'abc123!'}
        response = self.authenticated_regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class UserDetailTests(BaseAPITestCase):

    def setUp(self):

        # need an instance of a User to work with here
        self.establish_clients()
        pk = self.regular_user_1.pk

        self.url = reverse('user-detail', kwargs={'pk': pk})

    def test_user_detail_requires_auth(self):
        """
        Test that general requests to the endpoint generate 401
        """
        response = self.regular_client.get(self.url)
        self.assertTrue((response.status_code == status.HTTP_401_UNAUTHORIZED) 
        | (response.status_code == status.HTTP_403_FORBIDDEN))

    def test_admin_can_view_user(self):
        """
        Test that admins can view details about an individual User.
        """
        response = self.authenticated_admin_client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_email = response.data['email']
        self.assertEqual(response_email, self.regular_user_1.email)

    def test_users_can_view_own_detail(self):
        """
        Test that regular users can view info about themself.
        """
        response = self.authenticated_regular_client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_email = response.data['email']
        self.assertEqual(response_email, self.regular_user_1.email)

    def test_users_cannot_view_others_detail(self):
        """
        Test that regular users cannot look at other users
        """
        response = self.authenticated_other_client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class UserRegistrationTests(BaseAPITestCase):

    def setUp(self):
        self.url = reverse('user-register')
        self.establish_clients()     
        self.initial_user_uuids = set([str(x.pk) for x in User.objects.all()])

    def test_invalid_payload_rejected(self):
        '''
        Tests that payloads without the required keys
        get a 400 response
        '''

        # missing "confirm_password"
        payload = {'email': 'new_email@foo.com', 'password': 'abc123!'}
        response = self.regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # missing "password"
        payload = {'email': 'new_email@foo.com', 'confirm_password': 'abc123!'}
        response = self.regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # missing "email"
        payload = {'password': 'abc123!'}
        response = self.regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # check current instances unchanged:
        current_users = set([str(x.pk) for x in User.objects.all()])
        difference_set = current_users.difference(self.initial_user_uuids)
        self.assertEqual(len(difference_set), 0)


    def test_junk_password_rejected(self):
        '''
        Django has some functions for checking various elements of bad passwords.
        Check that the request is rejected and it has an appropriate warning
        '''
        # password confirm missing the final "!"
        payload = {'email': 'new_email@foo.com','password': 'abc123!', 'confirm_password': 'abc123'}
        response = self.regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue('password' in response.json())

        # check current instances unchanged:
        current_users = set([str(x.pk) for x in User.objects.all()])
        difference_set = current_users.difference(self.initial_user_uuids)
        self.assertEqual(len(difference_set), 0)

    def test_mismatched_password_rejected(self):
        '''
        We have a re-type password field-- so the two pwds must match
        the error can also be caught on the front-end, but we also 
        check here in case someone is directly interacting with the API
        '''
        # password confirm missing the final "!"
        payload = {'email': 'new_email@foo.com',
            'password': 'sksdf8aQ23!', 
            'confirm_password': 'sksdf8aQ23'}
        response = self.regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue('confirm_password' in response.json())

        # check current instances unchanged:
        current_users = set([str(x.pk) for x in User.objects.all()])
        difference_set = current_users.difference(self.initial_user_uuids)
        self.assertEqual(len(difference_set), 0)

    def test_successful_request_creates_inactive_user(self):
        '''
        If the request is properly formatted, a new user should be 
        created, but they should be marked as "inactive" until they 
        click on the link sent to their email
        '''
        payload = {'email': 'new_email@foo.com',
            'password': 'sksdf8aQ23!', 
            'confirm_password': 'sksdf8aQ23!'}
        response = self.regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # check current instances incremented:
        current_users = set([str(x.pk) for x in User.objects.all()])
        difference_set = current_users.difference(self.initial_user_uuids)
        self.assertEqual(len(difference_set), 1)

        # get that new user:
        new_user = User.objects.get(pk=list(difference_set)[0])
        self.assertFalse(new_user.is_active)

    @mock.patch('api.serializers.user.get_user_model')
    def test_failure_to_create_user(self, mock_user_model):
        '''
        If the user cannot be created (for some unspecified reason)
        then we return 500
        '''
        mock_model = mock.MagicMock()
        mock_ex = mock.MagicMock(side_effect=Exception('something wrong.'))
        mock_user_model.return_value = mock_model
        mock_model.objects.create_user = mock_ex
        payload = {'email': 'new_email@foo.com',
            'password': 'sksdf8aQ23!', 
            'confirm_password': 'sksdf8aQ23!'}
        response = self.regular_client.post(self.url, data=payload, format='json')        
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

        # check current instances unchanged:
        current_users = set([str(x.pk) for x in User.objects.all()])
        difference_set = current_users.difference(self.initial_user_uuids)
        self.assertEqual(len(difference_set), 0)