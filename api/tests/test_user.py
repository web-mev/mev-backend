import unittest.mock as mock
import uuid

from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ImproperlyConfigured
from rest_framework import status

from api.tests.base import BaseAPITestCase
from api.tests import test_settings
from api.utilities.basic_utils import encode_uid
from api.views import ResendActivationView, UserRegisterView

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

    @mock.patch('api.views.user_views.email_utils')
    def test_successful_request_creates_inactive_user(self, mock_email_utils):
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

        # check email method called:
        mock_email_utils.send_activation_email.assert_called()

        # check current instances incremented:
        current_users = set([str(x.pk) for x in User.objects.all()])
        difference_set = current_users.difference(self.initial_user_uuids)
        self.assertEqual(len(difference_set), 1)

        # get that new user:
        new_user = User.objects.get(pk=list(difference_set)[0])
        self.assertFalse(new_user.is_active)

    @mock.patch('api.serializers.user.User')
    def test_failure_to_create_user(self, mock_user_model):
        '''
        If the user cannot be created (for some unspecified reason)
        then we return 500
        '''
        mock_ex = mock.MagicMock(side_effect=Exception('something wrong.'))
        mock_user_model.objects.create_user = mock_ex
        payload = {'email': 'new_email@foo.com',
            'password': 'sksdf8aQ23!', 
            'confirm_password': 'sksdf8aQ23!'}
        response = self.regular_client.post(self.url, data=payload, format='json')        
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

        # check current instances unchanged:
        current_users = set([str(x.pk) for x in User.objects.all()])
        difference_set = current_users.difference(self.initial_user_uuids)
        self.assertEqual(len(difference_set), 0)

    def test_user_existed(self):
        '''
        If the user already existed, reject the request to register
        '''
        existing_user = User.objects.filter(is_active=True)[0]
        payload = {'email': existing_user.email,
            'password': 'sksdf8aQ23!', 
            'confirm_password': 'sksdf8aQ23!'}
        response = self.regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()['email'], UserRegisterView.EXISTING_USER_MESSAGE)

class UserActivateTests(BaseAPITestCase):

    def setUp(self):
        self.url = reverse('user-activate')
        self.establish_clients()

        # create an inactive user by modifying an existing:
        all_regular_users = User.objects.filter(
            is_staff = False
        )
        u = all_regular_users[0]
        u.is_active = False
        u.save()

        inactive_users = User.objects.filter(is_active=False)
        if len(inactive_users) == 0:
            raise ImproperlyConfigured('Need at least one inactive user.')
        self.inactive_user = inactive_users[0]

    def test_bad_payload_rejected(self):
        '''
        Test that 400 is raised if the payload does not have the
        proper contents
        '''
        payload = {'uid': 'junk'}
        response = self.regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bad_uid(self):
        '''
        Test that the payload format is correct, but the UID
        is invalid

        Test two things-- one is a UID that is correctly generated
        but corresponds to a non-existent user.

        The other tests just a bogus string that cannot be decoded
        '''
        user = self.inactive_user
        different_uuid = uuid.uuid4()
        if different_uuid == user.pk:
            raise ImproperlyConfigured('Somehow a randomly generated UUID'
                ' was equivalent to the user PK we are testing.')
        bad_uid = encode_uid(different_uuid)
        payload = {'uid': bad_uid, 'token': 'doesnotmatter'}
        response = self.regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue('uid' in response.json())

        bad_uid = 'asdfsadfsdfsdaf'
        payload = {'uid': bad_uid, 'token': 'doesnotmatter'}
        response = self.regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue('uid' in response.json())

        # query the user again to check that they are still inactive:
        updated_user = User.objects.get(pk=user.pk)
        self.assertFalse(updated_user.is_active)

    def test_bad_token(self):
        '''
        Test that the payload format is correct, but the token
        is invalid
        '''
        user = self.inactive_user
        other_user = None
        for u in User.objects.all():
            if u != user:
                other_user = u
                break

        # generate a valid token, but for a DIFFERENT user
        token = default_token_generator.make_token(other_user)
        uid = encode_uid(user.pk)
        payload = {'uid': uid, 'token': token}
        response = self.regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue('token' in response.json())

        # request with a garbage token
        token = 'asdfasdfasdfasd'
        uid = encode_uid(user.pk)
        payload = {'uid': uid, 'token': token}
        response = self.regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue('token' in response.json())

        # query the user again to check that they are still inactive:
        updated_user = User.objects.get(pk=user.pk)
        self.assertFalse(updated_user.is_active)

    @mock.patch('api.serializers.user.default_token_generator')
    def test_expired_token(self, mock_token_generator):
        '''
        Test that the payload format is correct, but the token
        has expired.  Can't really fake this, but just return False
        from the mocked check_token method.  Practically, this
        also tests all instances where the token validation fails.
        '''
        mock_token_generator.check_token.return_value = False

        user = self.inactive_user
        token = default_token_generator.make_token(user)
        uid = encode_uid(user.pk)
        payload = {'uid': uid, 'token': token}
        response = self.regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue('token' in response.json())

    def test_correct_request_activates_user(self):
        '''
        The user is set to active if the request succeeds
        '''
        user = self.inactive_user
        token = default_token_generator.make_token(user)
        uid = encode_uid(user.pk)
        payload = {'uid': uid, 'token': token}
        response = self.regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # query the user again to check that they are NOW active:
        updated_user = User.objects.get(pk=user.pk)
        self.assertTrue(updated_user.is_active)

    def test_previously_activated_user_does_nothing(self):
        '''
        If the user had previously been activated and used the link
        again, nothing happens.  Even if the token expired in the meantime.
        '''
        active_users = User.objects.filter(is_active=True)
        if len(active_users) == 0:
            raise ImproperlyConfigured('Need at least one active user.')
        user = active_users[0]
        token = default_token_generator.make_token(user)
        uid = encode_uid(user.pk)
        payload = {'uid': uid, 'token': token}
        response = self.regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # query the user again to check that they are still active:
        updated_user = User.objects.get(pk=user.pk)
        self.assertTrue(updated_user.is_active)

class ResendActivationTests(BaseAPITestCase):

    def setUp(self):
        self.url = reverse('resend-activation')
        self.establish_clients()

    def test_bad_payload_raises_exception(self):
        '''
        Bad payload, missing required key
        '''
        payload = {'email': 'junk'}
        response = self.regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_previously_activated_account_rejects_request(self):
        '''
        If the account is already active, reject the request
        to resend activation
        '''
        active_users = User.objects.filter(is_active=True)
        if len(active_users) == 0:
            raise ImproperlyConfigured('Need at least one active user.')
        user = active_users[0]
        payload = {'email': user.email}
        response = self.regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()['email'], ResendActivationView.ALREADY_ACTIVE_MESSAGE)

    def test_unknown_email_raises_exception(self):
        '''
        The email given in the payload is not found.
        Returns 400
        '''
        payload = {'email': test_settings.JUNK_EMAIL}
        response = self.regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
    @mock.patch('api.views.user_views.email_utils')
    def test_correctly_resends_email(self, mock_email_utils):
        '''
        The correct steps are performed when an inactive
        user requests a new activation email
        '''
        # create an inactive user by modifying an existing:
        all_regular_users = User.objects.filter(
            is_staff = False
        )
        u = all_regular_users[0]
        u.is_active = False
        u.save()

        inactive_users = User.objects.filter(is_active=False)
        if len(inactive_users) == 0:
            raise ImproperlyConfigured('Need at least one inactive user.')
        inactive_user = inactive_users[0]

        payload = {'email': inactive_user.email}
        response = self.regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        mock_email_utils.send_activation_email.assert_called()