import unittest.mock as mock

from django.urls import reverse
from django.test import override_settings
from django.db.utils import IntegrityError
from django.conf import settings

from globus_sdk.services.auth.errors import AuthAPIError

from exceptions import NonexistentGlobusTokenException

from api.tests.base import BaseAPITestCase
from api.models import GlobusTokens, GlobusTask
from api.utilities.globus import get_globus_token_from_db, \
    get_globus_tokens, \
    get_active_token, \
    session_is_recent, \
    refresh_globus_token, \
    check_globus_tokens


class GlobusUtilsTests(BaseAPITestCase):
    def setUp(self):
        self.establish_clients()

    def test_token_retrieval(self):
        '''
        Tests the function that handles retrieval of a GlobusTokens
        objects from the database
        '''
        # ensure we don't actually have any tokens in the db
        tokens = GlobusTokens.objects.all()
        self.assertTrue(len(tokens) == 0)

        self.assertIsNone(
            get_globus_token_from_db(
                self.regular_user_1, existence_required=False)
        )
        with self.assertRaises(NonexistentGlobusTokenException):
            get_globus_token_from_db(self.regular_user_1)

        # add a single token
        GlobusTokens.objects.create(user=self.regular_user_1, tokens={'abc':123})
        t = get_globus_token_from_db(self.regular_user_1)
        self.assertDictEqual(t.tokens, {'abc':123})

        # attempt add a second token for the user:
        with self.assertRaises(IntegrityError):
            GlobusTokens.objects.create(user=self.regular_user_1, tokens={'def':123})

    @mock.patch('api.utilities.globus.get_globus_token_from_db')
    def test_specific_globus_token_return(self, mock_get_db_token):

        t = GlobusTokens.objects.create(user=self.regular_user_1, tokens={'a':1, 'b':2})
        mock_get_db_token.return_value = t

        t1 = get_globus_tokens(self.regular_user_1)
        self.assertDictEqual(t1, {'a':1, 'b':2})

        t1 = get_globus_tokens(self.regular_user_1, None)
        self.assertDictEqual(t1, {'a':1, 'b':2})

        t2 = get_globus_tokens(self.regular_user_1, 'a')
        self.assertTrue(t2 == 1)

        with self.assertRaisesRegex(Exception, 'Unknown key'):
            get_globus_tokens(self.regular_user_1, 'x')

    @mock.patch('api.utilities.globus.refresh_globus_token')
    def test_get_active_token(self, mock_refresh_globus_token):
        mock_client = mock.MagicMock()
        mock_response = mock.MagicMock()
        mock_token = {'access_token': 'foo'}

        mock_response.data = {'active': True}
        mock_client.oauth2_validate_token.return_value = mock_response

        # first test for active token
        t = get_active_token(mock_client, mock_token, 's1')
        mock_refresh_globus_token.assert_not_called()
        self.assertEqual(t, mock_token)

        # now test that we attempt a refresh
        mock_refresh_globus_token.reset_mock()
        mock_refreshed_token_dict = {'s1': 'token1'}
        mock_refresh_globus_token.return_value = mock_refreshed_token_dict
        mock_response.data = {'active': False}
        t = get_active_token(mock_client, mock_token, 's1')
        mock_refresh_globus_token.assert_called_with(mock_client, mock_token)
        self.assertEqual(t, 'token1')

    @override_settings(GLOBUS_REAUTHENTICATION_WINDOW_IN_MINUTES=60)
    @mock.patch('api.utilities.globus.time')
    @mock.patch('api.utilities.globus.perform_token_introspection')
    def test_recent_session(self, mock_perform_token_introspection, mock_time):

        mock_client = mock.MagicMock()
        mock_auth_token = {'auth.globus.org': 'token content'}

        t0 = 100 # time in seconds
        introspection_data = {
            'sub': 'abc',
            'session_info': {
                'authentications': {
                    'abc': {
                        'auth_time': t0
                    }
                }
            }
        }
        # first mock being within the window where the session
        # is still valid
        mock_time.time.return_value = t0 + 60*5 # 5 minutes
        mock_perform_token_introspection.return_value = introspection_data

        self.assertTrue(session_is_recent(mock_client, mock_auth_token))

        # first mock being within the window where the session
        # is still valid
        mock_time.time.return_value = t0 + 60*120 # 120 minutes
        self.assertFalse(session_is_recent(mock_client, mock_auth_token))

        # now remove the session from the introspection data, which is
        # how the data looks if there were no sessions
        introspection_data = {
            'sub': 'abc',
            'session_info': {
                'authentications': {}
            }
        }
        # first mock being within the window where the session
        # is still valid
        mock_time.time.return_value = t0 + 60*5 # 5 minutes
        mock_perform_token_introspection.return_value = introspection_data
        self.assertFalse(session_is_recent(mock_client, mock_auth_token))

    @mock.patch('api.utilities.globus.alert_admins')
    def test_globus_token_refresh(self, mock_alert_admins):
        mock_client = mock.MagicMock()
        mock_response = mock.MagicMock()
        mock_response.http_status = 200
        mock_obj = mock.MagicMock()
        mock_response.by_resource_server = mock_obj
        mock_client.oauth2_refresh_token.return_value = mock_response
        t = refresh_globus_token(mock_client, {'refresh_token': 'foo'})
        self.assertEqual(mock_obj, t)

        mock_response.http_status = 400
        t = refresh_globus_token(mock_client, {'refresh_token': 'foo'})
        self.assertIsNone(t)
        mock_alert_admins.assert_called()

        mock_alert_admins.reset_mock()
        mock_err_response = mock.MagicMock()
        mock_err_response.status_code = 400
        mock_err_response.headers = {}
        mock_client.oauth2_refresh_token.side_effect = AuthAPIError(mock_err_response)
        t = refresh_globus_token(mock_client, {'refresh_token': 'foo'})
        self.assertIsNone(t)
        mock_alert_admins.assert_called()

    @mock.patch('api.utilities.globus.session_is_recent')
    @mock.patch('api.utilities.globus.update_tokens_in_db')
    @mock.patch('api.utilities.globus.get_globus_tokens')
    @mock.patch('api.utilities.globus.get_globus_client')
    @mock.patch('api.utilities.globus.get_active_token')
    def test_globus_token_check(self, \
        mock_get_active_token, \
        mock_get_globus_client, \
        mock_get_globus_tokens,\
        mock_update_tokens_in_db, \
        mock_session_is_recent):

        mock_client = mock.MagicMock()
        mock_get_globus_client.return_value = mock_client

        mock_get_active_token.return_value = 2
        mock_get_globus_tokens.return_value = {'auth.globus.org':1}

        mock_session_is_recent.return_value = True

        mock_user = mock.MagicMock()

        self.assertTrue(check_globus_tokens(mock_user))
        mock_session_is_recent.assert_called_with(mock_client, 2)
        mock_update_tokens_in_db.assert_called_with(mock_user, {'auth.globus.org': 2})

        # now mock an update failure (`get_active_token` returns None)
        mock_get_active_token.return_value = None
        mock_session_is_recent.reset_mock()
        self.assertFalse(check_globus_tokens(mock_user))
        mock_session_is_recent.assert_not_called()

class GlobusUploadTests(BaseAPITestCase):

    def setUp(self):
        self.globus_init_url = reverse('globus-init')
        self.globus_upload_url = reverse('globus-upload')
        self.establish_clients()

    @override_settings(GLOBUS_ENABLED=False)
    def test_disabled_globus_returns_400(self):
        headers = {'HTTP_ORIGIN':'foo'}
        r = self.authenticated_regular_client.get(self.globus_init_url, **headers)
        self.assertEqual(r.status_code, 400)

    @override_settings(GLOBUS_ENABLED=True)
    def test_enabled_globus_returns_200(self):
        headers = {'HTTP_ORIGIN':'foo'}
        r = self.authenticated_regular_client.get(self.globus_init_url, **headers)
        self.assertEqual(r.status_code, 200)