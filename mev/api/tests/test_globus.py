import unittest.mock as mock
import uuid

from django.urls import reverse
from django.test import override_settings
from django.db.utils import IntegrityError
from django.conf import settings

from globus_sdk.services.auth.errors import AuthAPIError
from globus_sdk import TransferAPIError

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
        GlobusTokens.objects.create(
            user=self.regular_user_1, tokens={'abc': 123})
        t = get_globus_token_from_db(self.regular_user_1)
        self.assertDictEqual(t.tokens, {'abc': 123})

        # attempt add a second token for the user:
        with self.assertRaises(IntegrityError):
            GlobusTokens.objects.create(
                user=self.regular_user_1, tokens={'def': 123})

    @mock.patch('api.utilities.globus.get_globus_token_from_db')
    def test_specific_globus_token_return(self, mock_get_db_token):

        t = GlobusTokens.objects.create(
            user=self.regular_user_1, tokens={'a': 1, 'b': 2})
        mock_get_db_token.return_value = t

        t1 = get_globus_tokens(self.regular_user_1)
        self.assertDictEqual(t1, {'a': 1, 'b': 2})

        t1 = get_globus_tokens(self.regular_user_1, None)
        self.assertDictEqual(t1, {'a': 1, 'b': 2})

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

        t0 = 100  # time in seconds
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
        mock_time.time.return_value = t0 + 60*5  # 5 minutes
        mock_perform_token_introspection.return_value = introspection_data

        self.assertTrue(session_is_recent(mock_client, mock_auth_token))

        # first mock being within the window where the session
        # is still valid
        mock_time.time.return_value = t0 + 60*120  # 120 minutes
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
        mock_time.time.return_value = t0 + 60*5  # 5 minutes
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
        mock_client.oauth2_refresh_token.side_effect = AuthAPIError(
            mock_err_response)
        t = refresh_globus_token(mock_client, {'refresh_token': 'foo'})
        self.assertIsNone(t)
        mock_alert_admins.assert_called()

    @mock.patch('api.utilities.globus.session_is_recent')
    @mock.patch('api.utilities.globus.update_tokens_in_db')
    @mock.patch('api.utilities.globus.get_globus_tokens')
    @mock.patch('api.utilities.globus.get_globus_client')
    @mock.patch('api.utilities.globus.get_active_token')
    def test_globus_token_check(self,
                                mock_get_active_token,
                                mock_get_globus_client,
                                mock_get_globus_tokens,
                                mock_update_tokens_in_db,
                                mock_session_is_recent):

        mock_client = mock.MagicMock()
        mock_get_globus_client.return_value = mock_client

        mock_get_active_token.return_value = 2
        mock_get_globus_tokens.return_value = {'auth.globus.org': 1}

        mock_session_is_recent.return_value = True

        mock_user = mock.MagicMock()

        self.assertTrue(check_globus_tokens(mock_user))
        mock_session_is_recent.assert_called_with(mock_client, 2)
        mock_update_tokens_in_db.assert_called_with(
            mock_user, {'auth.globus.org': 2})

        # now mock an update failure (`get_active_token` returns None)
        mock_get_active_token.return_value = None
        mock_session_is_recent.reset_mock()
        self.assertFalse(check_globus_tokens(mock_user))
        mock_session_is_recent.assert_not_called()


class GlobusUploadTests(BaseAPITestCase):

    def setUp(self):
        self.globus_upload_url = reverse('globus-upload')
        self.establish_clients()

    @override_settings(GLOBUS_ENABLED=True, GLOBUS_ENDPOINT_ID='dest_id')
    @mock.patch('api.views.globus_views.poll_globus_task')
    @mock.patch('api.views.globus_views.create_application_transfer_client')
    @mock.patch('api.views.globus_views.create_user_transfer_client')
    @mock.patch('api.views.globus_views.get_globus_uuid')
    @mock.patch('api.views.globus_views.globus_sdk')
    @mock.patch('api.views.globus_views.uuid')
    def test_upload(self, mock_uuid,
        mock_globus_sdk,
        mock_get_globus_uuid,
        mock_create_user_transfer_client, 
        mock_create_application_transfer_client,
        mock_poll_globus_task):

        mock_payload = {
            'params': {
                'label': 'some label', 
                'endpoint': 'abc123', 
                'path': '/home/folder', 
                'endpoint_id': 'source_id', 
                'entity_type': '...', 
                'high_assurance': 'false', 
                'file[0]': 'f0.txt', 
                'file[1]': 'f1.txt', 
                'action': 'http://localhost:4200/globus/upload-redirect/', 
                'method': 'GET'
            }
        }
        # need this mock to set the 'temp' folder in globus
        u = uuid.uuid4()
        mock_uuid.uuid4.return_value = u

        mock_transfer_data = mock.MagicMock()
        mock_globus_sdk.TransferData.return_value = mock_transfer_data

        mock_get_globus_uuid.return_value = str(uuid.uuid4())

        mock_app_transfer_client = mock.MagicMock()
        mock_user_transfer_client = mock.MagicMock()
        mock_app_transfer_client.add_endpoint_acl_rule.return_value = {'access_id': 'some_rule_id'}
        mock_user_transfer_client.submit_transfer.return_value = {'task_id': 'my_task_id'}
        mock_user_transfer_client.get_task.return_value = {'label': mock_payload['params']['label']}
        mock_create_application_transfer_client.return_value = mock_app_transfer_client
        mock_create_user_transfer_client.return_value = mock_user_transfer_client

        headers = {'HTTP_ORIGIN': 'foo'}
        r = self.authenticated_regular_client.post(
            self.globus_upload_url, 
            data=mock_payload, 
            format='json', 
            **headers)
        j = r.json()
        self.assertTrue(j['transfer_id'] == 'my_task_id')
        mock_app_transfer_client.add_endpoint_acl_rule.assert_called()
        mock_transfer_data.add_item.assert_has_calls([
            mock.call(source_path='/home/folder/f0.txt', destination_path=f'/tmp-{u}/f0.txt'),
            mock.call(source_path='/home/folder/f1.txt', destination_path=f'/tmp-{u}/f1.txt'),
        ])
        mock_user_transfer_client.endpoint_autoactivate.assert_has_calls([
            mock.call('source_id'),
            mock.call('dest_id')
        ])
        mock_user_transfer_client.submit_transfer.assert_called_with(mock_transfer_data)
        mock_user_transfer_client.get_task.assert_called_with('my_task_id')
        mock_poll_globus_task.delay.assert_called_with('my_task_id')

        tasks = GlobusTask.objects.filter(user=self.regular_user_1)
        self.assertTrue(len(tasks) == 1)
        task = tasks[0]
        self.assertTrue(task.task_id == 'my_task_id')
        self.assertTrue(task.rule_id == 'some_rule_id')
        self.assertTrue(task.label == mock_payload['params']['label'])

    @override_settings(GLOBUS_ENABLED=True, GLOBUS_ENDPOINT_ID='dest_id')
    @mock.patch('api.views.globus_views.poll_globus_task')
    @mock.patch('api.views.globus_views.create_application_transfer_client')
    @mock.patch('api.views.globus_views.create_user_transfer_client')
    @mock.patch('api.views.globus_views.get_globus_uuid')
    @mock.patch('api.views.globus_views.globus_sdk')
    @mock.patch('api.views.globus_views.uuid')
    def test_upload_submission_error_caught(self, mock_uuid,
        mock_globus_sdk,
        mock_get_globus_uuid,
        mock_create_user_transfer_client, 
        mock_create_application_transfer_client,
        mock_poll_globus_task):

        mock_payload = {
            'params': {
                'label': 'some label', 
                'endpoint': 'abc123', 
                'path': '/home/folder', 
                'endpoint_id': 'source_id', 
                'entity_type': '...', 
                'high_assurance': 'false', 
                'file[0]': 'f0.txt', 
                'file[1]': 'f1.txt', 
                'action': 'http://localhost:4200/globus/upload-redirect/', 
                'method': 'GET'
            }
        }
        # need this mock to set the 'temp' folder in globus
        u = uuid.uuid4()
        mock_uuid.uuid4.return_value = u

        mock_transfer_data = mock.MagicMock()
        mock_globus_sdk.TransferData.return_value = mock_transfer_data

        mock_get_globus_uuid.return_value = str(uuid.uuid4())

        mock_app_transfer_client = mock.MagicMock()
        mock_user_transfer_client = mock.MagicMock()
        mock_app_transfer_client.add_endpoint_acl_rule.return_value = {'access_id': 'some_rule_id'}
        mock_err_response = mock.MagicMock()
        mock_err_response.status_code = 400
        mock_err_response.headers = {}
        mock_user_transfer_client.submit_transfer.side_effect = TransferAPIError(mock_err_response)
        mock_create_application_transfer_client.return_value = mock_app_transfer_client
        mock_create_user_transfer_client.return_value = mock_user_transfer_client

        headers = {'HTTP_ORIGIN': 'foo'}
        r = self.authenticated_regular_client.post(
            self.globus_upload_url, 
            data=mock_payload, 
            format='json', 
            **headers)
        j = r.json()
        self.assertTrue(j['transfer_id'] is None)
        mock_app_transfer_client.add_endpoint_acl_rule.assert_called()
        mock_transfer_data.add_item.assert_has_calls([
            mock.call(source_path='/home/folder/f0.txt', destination_path=f'/tmp-{u}/f0.txt'),
            mock.call(source_path='/home/folder/f1.txt', destination_path=f'/tmp-{u}/f1.txt'),
        ])
        mock_user_transfer_client.endpoint_autoactivate.assert_has_calls([
            mock.call('source_id'),
            mock.call('dest_id')
        ])
        mock_user_transfer_client.submit_transfer.assert_called_with(mock_transfer_data)
        mock_poll_globus_task.delay.assert_not_called()

        tasks = GlobusTask.objects.filter(user=self.regular_user_1)
        self.assertTrue(len(tasks) == 0)

    @override_settings(GLOBUS_ENABLED=False)
    def test_disabled_globus_returns_400(self):
        headers = {'HTTP_ORIGIN': 'foo'}
        r = self.authenticated_regular_client.post(
            self.globus_upload_url,
            data={}, 
            format='json',
            **headers)
        self.assertEqual(r.status_code, 400)


class GlobusInitTests(BaseAPITestCase):

    def setUp(self):
        self.globus_init_url = reverse('globus-init')
        self.globus_upload_url = reverse('globus-upload')
        self.establish_clients()

    @override_settings(GLOBUS_ENABLED=False)
    def test_disabled_globus_returns_400(self):
        headers = {'HTTP_ORIGIN': 'foo'}
        r = self.authenticated_regular_client.get(
            self.globus_init_url, **headers)
        self.assertEqual(r.status_code, 400)

    @override_settings(GLOBUS_ENABLED=True)
    def test_globus_returns_auth_url_for_new_user(self):
        '''
        This tests the situation where a user does not have existing Globus
        tokens, so we need to start the OAuth2 flow
        '''
        headers = {'HTTP_ORIGIN': 'foo'}
        r = self.authenticated_regular_client.get(
            self.globus_init_url, **headers)
        self.assertEqual(r.status_code, 200)
        j = r.json()
        # this user did NOT have tokens, so we get back an auth url
        self.assertTrue('globus-auth-url' in j)

    @override_settings(GLOBUS_ENABLED=True)
    @mock.patch('api.views.globus_views.get_globus_token_from_db')
    @mock.patch('api.views.globus_views.check_globus_tokens')
    def test_globus_returns_browser_url_for_existing_user(self,
            mock_check_globus_tokens,
            mock_get_globus_token_from_db):
        '''
        This tests the situation where a user has an existing Globus
        tokens (with a recent session), so we direct them to the Globus
        file browser/chooser
        '''
        mock_get_globus_token_from_db.return_value = 'something'
        mock_check_globus_tokens.return_value = True

        headers = {'HTTP_ORIGIN': 'foo'}
        url = f'{self.globus_init_url}?direction=upload'
        r = self.authenticated_regular_client.get(url, **headers)
        self.assertEqual(r.status_code, 200)
        j = r.json()

        # this user had recent tokens, so we get back a browser url
        self.assertTrue('globus-browser-url' in j)
        mock_get_globus_token_from_db.assert_called_with(
            self.regular_user_1, existence_required=False)
        mock_check_globus_tokens.assert_called_with(self.regular_user_1)

    @override_settings(GLOBUS_ENABLED=True)
    @mock.patch('api.views.globus_views.get_globus_uuid')
    @mock.patch('api.views.globus_views.get_globus_token_from_db')
    @mock.patch('api.views.globus_views.check_globus_tokens')
    def test_globus_returns_auth_url_for_existing_user(self,
            mock_check_globus_tokens,
            mock_get_globus_token_from_db,
            mock_get_globus_uuid):
        '''
        This tests the situation where a user has an existing Globus
        tokens (but without a recent session), so we direct them to
        globus auth
        '''
        mock_get_globus_token_from_db.return_value = 'something'
        # False mocks there not being a recent session (or a token update failure),
        # which should force a re-auth
        mock_check_globus_tokens.return_value = False
        u = str(uuid.uuid4())
        mock_get_globus_uuid.return_value = u

        headers = {'HTTP_ORIGIN': 'foo'}
        url = f'{self.globus_init_url}?direction=upload'
        r = self.authenticated_regular_client.get(url, **headers)
        self.assertEqual(r.status_code, 200)
        j = r.json()
        self.assertTrue('globus-auth-url' in j)

    @override_settings(GLOBUS_ENABLED=True)
    @mock.patch('api.views.globus_views.get_globus_client')
    @mock.patch('api.views.globus_views.create_or_update_token')
    def test_oauth2_code_request(self, mock_create_or_update_token,
                                 mock_get_globus_client):
        '''
        Tests the leg of the oauth2 flow where the backend receives the code
        '''
        mock_client = mock.MagicMock()
        mock_tokens = mock.MagicMock()
        mock_tokens.by_resource_server = {'a': 1}
        mock_client.oauth2_exchange_code_for_tokens.return_value = mock_tokens
        mock_get_globus_client.return_value = mock_client
        headers = {'HTTP_ORIGIN': 'foo'}
        url = f'{self.globus_init_url}?direction=upload&code=foo'
        r = self.authenticated_regular_client.get(url, **headers)
        j = r.json()
        self.assertTrue('globus-browser-url' in j)
        mock_create_or_update_token.assert_called_with(
            self.regular_user_1, {'a': 1})
