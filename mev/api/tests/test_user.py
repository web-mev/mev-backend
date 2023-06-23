import unittest.mock as mock
import uuid

from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ImproperlyConfigured
from rest_framework import status
from rest_framework.test import APIClient
from social_django.models import UserSocialAuth

from api.tests.base import BaseAPITestCase
from api.tests import test_settings
from api.utilities.basic_utils import encode_uid
from api.views import ResendActivationView, UserRegisterView

User = get_user_model()

class UserInactiveTests(BaseAPITestCase):

    def test_inactive(self):
        '''
        Test that inactive users can't login
        '''
        passwd = 'some!dummy!pswd@'
        new_user = User.objects.create_user(
            'some_email@gmail.com',
            passwd
        )
        new_user.is_active = False
        new_user.save()

        client = APIClient()
        logged_in = client.login(email=new_user.email, password=passwd)
        self.assertFalse(logged_in)
       

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

    def test_admin_cannot_list_user(self):
        """
        Test that admins can only view their own info
        """
        response = self.authenticated_admin_client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        received_user_emails = set([x['email'] for x in response.data])
        self.assertEqual([self.admin_user.email], list(received_user_emails))

    def test_admin_cannot_create_user(self):
        """
        Test that even admins can't create a User
        """
        # get all initial instances before anything happens:
        initial_users = set([str(x.pk) for x in User.objects.all()])

        payload = {'email': 'new_email@foo.com', 'password': 'abc123!'}
        response = self.authenticated_admin_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # get current instances and check nothing was created
        current_users = set([str(x.pk) for x in User.objects.all()])
        difference_set = current_users.difference(initial_users)
        self.assertEqual(len(difference_set), 0)

    def test_regular_user_cannot_list(self):
        """
        Test that regular users can't list users
        """
        response = self.authenticated_regular_client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        j = response.json()
        self.assertTrue(len(j)==1)
        info = j[0]
        self.assertEqual(info['email'], self.regular_user_1.email)

    def test_regular_user_cannot_create_user(self):
        """
        Test that regular users can't create new users
        """
        # get all initial instances before anything happens:
        initial_users = set([str(x.pk) for x in User.objects.all()])

        payload = {'email': 'new_email@foo.com', 'password': 'abc123!'}
        response = self.authenticated_regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


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

    def test_admin_cannot_view_user(self):
        """
        Test that admins can't view details about an individual User.
        """
        response = self.authenticated_admin_client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # CAN see info about themself, though.
        url = reverse('user-detail', kwargs={'pk': self.admin_user.pk})
        response = self.authenticated_admin_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_email = response.data['email']
        self.assertEqual(response_email, self.admin_user.email)

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


class PasswordResetTests(BaseAPITestCase):

    def setUp(self):
        self.url = reverse('password-reset')
        self.establish_clients()

    def test_bad_payload_raises_exception(self):
        '''
        Bad payload, missing required key
        '''
        payload = {'email': 'junk'}
        response = self.regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_passwordless_account_fails(self):
        '''
        Accounts generated from social authentication (e.g. google)
        do not have a password set.  For those, we reject the request
        since it does not make sense
        '''
        # check that we have a user in our test database that makes sense
        # for this test
        user = User.objects.create_user(test_settings.SOCIAL_AUTH_EMAIL)
        users_without_passwords = []
        for u in User.objects.all():
            if not u.has_usable_password():
                users_without_passwords.append(u)
        if len(users_without_passwords) == 0:
            raise ImproperlyConfigured('Need at least one user'
                ' whose `has_usable_password` evaluates to False'
            )
        test_user = users_without_passwords[0]
        payload = {'email': test_user.email}
        response = self.regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_email_raises_exception(self):
        '''
        The email given in the payload is not found.
        Returns 400
        '''
        payload = {'email': test_settings.JUNK_EMAIL}
        response = self.regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
    @mock.patch('api.views.user_views.email_utils')
    def test_correctly_sends_email(self, mock_email_utils):
        '''
        The correct steps are performed when a
        user requests a password reset
        '''
        # get users for whom we can reset a password:
        users_with_passwords = []
        for u in User.objects.all():
            if u.has_usable_password():
                users_with_passwords.append(u)
        
        if len(users_with_passwords) == 0:
            raise ImproperlyConfigured('Need at least one user'
                ' whose `has_usable_password` evaluates to True'
            )

        u = users_with_passwords[0]
        payload = {'email': u.email}
        response = self.regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        mock_email_utils.send_password_reset_email.assert_called()


class PasswordResetConfirmTests(BaseAPITestCase):
    '''
    Tests the endpont where the user has clicked on the email,
    and is requesting a reset with a uid, token, pwd, and retyped pwd
    '''
    def setUp(self):
        self.url = reverse('password-reset-confirm')
        self.establish_clients()

        self.test_user = self.regular_user_1

    def test_bad_payload_raises_exception(self):
        '''
        Bad payload, missing required key
        '''
        payload = {'uid': 'junk'}
        response = self.regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        uid = encode_uid(self.test_user.pk)
        token = default_token_generator.make_token(self.test_user)
        pwd = 'some_new_password123!'

        payload = {
            'uid': uid,
            'token': token,
            'password' : pwd,
            'confirm_password': pwd + '!!'
        }
        response = self.regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_successful_reset(self):
        '''
        Tests that a proper rest works.
        '''
        uid = encode_uid(self.test_user.pk)
        token = default_token_generator.make_token(self.test_user)
        pwd = 'some_new_password123!'

        payload = {
            'uid': uid,
            'token': token,
            'password' : pwd,
            'confirm_password': pwd
        }
        response = self.regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # check that a bad password doesn't work
        logged_in = self.regular_client.login(email=self.test_user.email, password=pwd+'!!!')
        self.assertFalse(logged_in)

        # and test that the new password allows login
        logged_in = self.regular_client.login(email=self.test_user.email, password=pwd)
        self.assertTrue(logged_in)

class PasswordChangeTests(BaseAPITestCase):
    '''
    Tests the endpont where the user is authenticated/logged in,
    and is requesting a password change
    '''
    def setUp(self):
        self.url = reverse('password-change')
        self.establish_clients()

        self.test_user = self.regular_user_1
        self.current_password = test_settings.REGULAR_USER_1_PASSWORD

    def test_must_be_authenticated(self):
        '''
        To change the password, you need to be authenticated already
        '''

        new_pwd = 'some_new_password123!'
        payload = {
            'current_password': self.current_password,
            'password': new_pwd,
            'confirm_password': new_pwd
        }

        response = self.regular_client.post(
            self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # check that they can still login with the old password
        logged_in = self.regular_client.login(email=self.test_user.email, password=self.current_password)
        self.assertTrue(logged_in)

    def test_bad_current_password(self):

        new_pwd = 'some_new_password123!'
        payload = {
            'current_password': self.current_password + 'junk',
            'password': new_pwd,
            'confirm_password': new_pwd
        }

        response = self.authenticated_regular_client.post(
            self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue('current_password' in response.json())

        # check that they can still login with the old password
        logged_in = self.regular_client.login(email=self.test_user.email, password=self.current_password)
        self.assertTrue(logged_in)

    def test_mismatched_new_passwords(self):

        new_pwd = 'some_new_password123!'
        payload = {
            'current_password': self.current_password,
            'password': new_pwd,
            'confirm_password': new_pwd + '!!' # to make it different
        }

        response = self.authenticated_regular_client.post(
            self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue('confirm_password' in response.json())

        # check that they can still login with the old password
        logged_in = self.regular_client.login(email=self.test_user.email, password=self.current_password)
        self.assertTrue(logged_in)

    def test_successful_change(self):

        new_pwd = 'some_new_password123!'
        payload = {
            'current_password': self.current_password,
            'password': new_pwd,
            'confirm_password': new_pwd
        }

        response = self.authenticated_regular_client.post(
            self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        logged_in = self.regular_client.login(email=self.test_user.email, password=new_pwd)
        self.assertTrue(logged_in)

    def test_reject_change_when_inactive_password(self):
        '''
        If a user first registers via social and then tries to change their
        password, then we let them know
        '''
        # when a social user is created, it involves creating a 
        # 'password-free' user and a social auth user:
        email = 'some_email@gmail.com'
        new_user = User.objects.create_user(email)
        self.assertFalse(new_user.has_usable_password())
        new_user.is_active = True
        new_user.save()

        # now, create the social auth association. This is what
        # would happen if a user initially employed a social auth
        # strategy (e.g. google) to register
        UserSocialAuth.objects.create(user=new_user)
        u = User.objects.get(email=email)
        self.assertTrue(len(u.social_auth.all()) > 0)

        new_pwd = 'some_new_password123!'
        payload = {
            'current_password': 'something',
            'password': new_pwd,
            'confirm_password': new_pwd
        }
        authenticated_client = APIClient()
        authenticated_client.force_authenticate(user=u)
        response = authenticated_client.post(
            self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        j = response.json()
        self.assertTrue('third-party identity provider' in j['current_password'][0])


class TestTokenViews(BaseAPITestCase):

    def setUp(self):
        self.establish_clients()

    def test_both_logins_permitted(self):
        '''
        If a user first establishes an account with email/pass and subsequently
        uses the social mechanism for the same email, assert that we can still
        log them in via email/password.
        '''
        # first test the 'proper' case where a user who has registered
        # via email/pwd correctly receives back a token pair
        passwd = 'some!dummy!pswd@'
        email = 'some_email@gmail.com'
        new_user = User.objects.create_user(
            email,
            passwd
        )
        new_user.is_active = True
        new_user.save()

        url = reverse('token_obtain_pair')
        payload = {
            'email': email,
            'password': passwd
        }
        response = self.regular_client.post(
            url, data=payload, format='json')
        j = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue('refresh' in j.keys())
        self.assertTrue('access' in j.keys())

        # now, create the social auth association. This is what
        # would happen if a user subsequently employed a social auth
        # strategy (e.g. google) to login AFTER they created the
        # account via email/password
        UserSocialAuth.objects.create(user=new_user)
        u = User.objects.get(email=email)
        self.assertTrue(len(u.social_auth.all()) > 0)

        # Given that the user has a social auth association,
        # a request to authenticate with email/pwd should be
        # rejected with a helpful message
        response = self.regular_client.post(
            url, data=payload, format='json')
        j = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue('refresh' in j.keys())
        self.assertTrue('access' in j.keys())

    def test_login_mixup_is_indicated(self):
        '''
        If a user first registers via social and then tries to login via
        email, confirm that we let them know
        '''
        # when a social user is created, it involves creating a 
        # 'password-free' user and a social auth user:
        email = 'some_email@gmail.com'
        new_user = User.objects.create_user(email)
        self.assertFalse(new_user.has_usable_password())
        new_user.is_active = True
        new_user.save()

        # now, create the social auth association. This is what
        # would happen if a user initially employed a social auth
        # strategy (e.g. google) to register
        UserSocialAuth.objects.create(user=new_user)
        u = User.objects.get(email=email)
        self.assertTrue(len(u.social_auth.all()) > 0)

        # Given that the user has a social auth association,
        # a request to authenticate with email/pwd should be
        # rejected with a helpful message
        url = reverse('token_obtain_pair')
        payload = {
            'email': email,
            'password': 'some random guess'
        }
        response = self.regular_client.post(
            url, data=payload, format='json')
        j = response.json()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue('already been registered' in j['non_field_errors'])