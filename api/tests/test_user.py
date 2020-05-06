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
        Test that general requests to the endpoint generate 403
        """
        response = self.regular_client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

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
        Test that general requests to the endpoint generate 403
        """
        response = self.regular_client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

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