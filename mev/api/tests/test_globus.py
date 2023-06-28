import unittest.mock as mock
import uuid
from io import BytesIO

from django.urls import reverse
from django.test import override_settings
from django.db.utils import IntegrityError
from django.conf import settings
from django.core.files import File

from globus_sdk.services.auth.errors import AuthAPIError
from globus_sdk import TransferAPIError

from exceptions import NonexistentGlobusTokenException

from api.tests.base import BaseAPITestCase
from api.models import GlobusTokens, \
    GlobusTask, \
    Resource
from api.utilities.globus import get_globus_token_from_db, \
    get_globus_tokens, \
    get_active_token, \
    session_is_recent, \
    refresh_globus_token, \
    check_globus_tokens, \
    submit_transfer, \
    post_upload, \
    add_acl_rule, \
    delete_acl_rule, \
    GLOBUS_UPLOAD, \
    GLOBUS_DOWNLOAD
from api.async_tasks.globus_tasks import poll_globus_task, \
    perform_globus_download

class GlobusAsyncTests(BaseAPITestCase):
    def setUp(self):
        self.establish_clients()

    @mock.patch('api.async_tasks.globus_tasks.delete_acl_rule')
    @mock.patch('api.async_tasks.globus_tasks.post_upload')
    @mock.patch('api.async_tasks.globus_tasks.create_user_transfer_client')
    def test_poll_globus_task_for_upload(self, mock_create_user_transfer_client, 
        mock_post_upload, mock_delete_acl_rule):
        task_id = uuid.uuid4()
        gt = GlobusTask.objects.create(
            user=self.regular_user_1,
            task_id=task_id,
            rule_id='myrule',
            label='some label'
        )

        mock_client = mock.MagicMock()
        # mocks the transfer being complete-
        mock_client.task_wait.return_value = True
        mock_create_user_transfer_client.return_value = mock_client
        
        poll_globus_task(task_id, GLOBUS_UPLOAD)
        mock_post_upload.assert_called_with(task_id, self.regular_user_1)

        # query the task to see that it's marked as completed
        gt2 = GlobusTask.objects.get(pk=gt.pk)
        self.assertTrue(gt2.transfer_complete)

    @mock.patch('api.async_tasks.globus_tasks.delete_acl_rule')
    @mock.patch('api.async_tasks.globus_tasks.post_upload')
    @mock.patch('api.async_tasks.globus_tasks.create_user_transfer_client')
    def test_poll_globus_task_for_download(self, mock_create_user_transfer_client, 
        mock_post_upload, mock_delete_acl_rule):
        task_id = uuid.uuid4()
        gt = GlobusTask.objects.create(
            user=self.regular_user_1,
            task_id=task_id,
            rule_id='myrule',
            label='some label'
        )

        mock_client = mock.MagicMock()
        # mocks the transfer being complete-
        mock_client.task_wait.return_value = True
        mock_create_user_transfer_client.return_value = mock_client
        
        poll_globus_task(task_id, GLOBUS_DOWNLOAD)
        mock_post_upload.assert_not_called()

        # query the task to see that it's marked as completed
        gt2 = GlobusTask.objects.get(pk=gt.pk)
        self.assertTrue(gt2.transfer_complete)

    @override_settings(GLOBUS_BUCKET='my-globus-bucket', 
        GLOBUS_ENDPOINT_ID='my_endpoint_id')
    @mock.patch('api.async_tasks.globus_tasks.create_application_transfer_client')
    @mock.patch('api.async_tasks.globus_tasks.create_user_transfer_client')
    @mock.patch('api.async_tasks.globus_tasks.get_globus_uuid')
    @mock.patch('api.async_tasks.globus_tasks.default_storage')
    @mock.patch('api.async_tasks.globus_tasks.add_acl_rule')
    @mock.patch('api.async_tasks.globus_tasks.TransferData')
    @mock.patch('api.async_tasks.globus_tasks.submit_transfer')
    @mock.patch('api.async_tasks.globus_tasks.poll_globus_task')
    @mock.patch('api.async_tasks.globus_tasks.uuid')
    def test_download(self,
        mock_uuid,
        mock_poll_globus_task,
        mock_submit_transfer,
        mock_TransferData,
        mock_add_acl_rule,
        mock_default_storage,
        mock_get_globus_uuid,
        mock_create_user_transfer_client,
        mock_create_application_transfer_client):

        mock_app_tc = mock.MagicMock()
        mock_user_tc = mock.MagicMock()
        mock_user_tc.get_task.return_value = {'label': 'some label'}
        mock_transfer_data = mock.MagicMock()
        globus_user_uuid = uuid.uuid4()
        globus_tmp_uuid = uuid.uuid4()
        mock_task_id = uuid.uuid4()
        mock_rule_id = 'some-rule-id'

        mock_create_application_transfer_client.return_value = mock_app_tc
        mock_create_user_transfer_client.return_value = mock_user_tc
        mock_get_globus_uuid.return_value = globus_user_uuid
        mock_default_storage.copy_out_to_bucket.side_effect = [
            'path/to/dest/f0.txt',
            'path/to/dest/f1.txt'
        ]
        mock_uuid.uuid4.return_value = globus_tmp_uuid
        mock_TransferData.return_value = mock_transfer_data
        mock_submit_transfer.return_value = mock_task_id
        mock_add_acl_rule.return_value = mock_rule_id

        user_pk = self.regular_user_1.pk
        r0 = Resource.objects.create(
            name='foo.txt',
            owner = self.regular_user_1,
            datafile = File(BytesIO(), 'foo.txt')
        )
        r1 = Resource.objects.create(
            name='bar.txt',
            owner = self.regular_user_1,
            datafile = File(BytesIO(), 'bar.txt')
        )
        request_data = {
            'label': 'mylabel',
            'endpoint_id': 'my_endpoint_id',
            'path': '/rootpath'
        }
        gt0 = GlobusTask.objects.filter(user=self.regular_user_1)
        self.assertTrue(len(gt0)==0)
        perform_globus_download(
            [r0.pk, r1.pk],
            user_pk,
            request_data
        )
        mock_default_storage.copy_out_to_bucket.assert_has_calls([
            mock.call(r0, 'my-globus-bucket', f'tmp-{globus_tmp_uuid}/foo.txt'),
            mock.call(r1, 'my-globus-bucket', f'tmp-{globus_tmp_uuid}/bar.txt')
        ])
        mock_transfer_data.add_item.assert_has_calls([
            mock.call(
                source_path=f'tmp-{globus_tmp_uuid}/foo.txt',
                destination_path='/rootpath/foo.txt'),
            mock.call(
                source_path=f'tmp-{globus_tmp_uuid}/bar.txt',
                destination_path='/rootpath/bar.txt'),
        ])
        mock_submit_transfer.assert_called_with(mock_user_tc, mock_transfer_data)
        mock_poll_globus_task.assert_called_with(mock_task_id, GLOBUS_DOWNLOAD)
        gt1 = GlobusTask.objects.filter(user=self.regular_user_1)
        self.assertTrue(len(gt1) == 1)
        self.assertTrue(gt1[0].task_id == str(mock_task_id))

        # now mock a submission failure and check that we show this in the db
        mock_default_storage.reset_mock()
        mock_default_storage.copy_out_to_bucket.side_effect = [
            'path/to/dest/f0.txt',
            'path/to/dest/f1.txt'
        ]
        mock_transfer_data.reset_mock()
        mock_submit_transfer.reset_mock()
        mock_poll_globus_task.reset_mock()
        failed_submissions = GlobusTask.objects.filter(user=self.regular_user_1, submission_failure=True)
        self.assertTrue(len(failed_submissions)==0)
        mock_submit_transfer.return_value = None
        perform_globus_download(
            [r0.pk, r1.pk],
            user_pk,
            request_data
        )
        failed_submissions = GlobusTask.objects.filter(user=self.regular_user_1, submission_failure=True)
        self.assertTrue(len(failed_submissions)==1)
        mock_default_storage.copy_out_to_bucket.assert_has_calls([
            mock.call(r0, 'my-globus-bucket', f'tmp-{globus_tmp_uuid}/foo.txt'),
            mock.call(r1, 'my-globus-bucket', f'tmp-{globus_tmp_uuid}/bar.txt')
        ])
        mock_transfer_data.add_item.assert_has_calls([
            mock.call(
                source_path=f'tmp-{globus_tmp_uuid}/foo.txt',
                destination_path='/rootpath/foo.txt'),
            mock.call(
                source_path=f'tmp-{globus_tmp_uuid}/bar.txt',
                destination_path='/rootpath/bar.txt'),
        ])
        mock_submit_transfer.assert_called_with(mock_user_tc, mock_transfer_data)
        mock_poll_globus_task.assert_not_called()



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

    @mock.patch('api.utilities.globus.alert_admins')
    def test_submit_transfer(self, mock_alert_admins):
        mock_transfer_client = mock.MagicMock()
        mock_transfer_client.submit_transfer.return_value = {'task_id': 'my_task_id'}
        mock_transfer_data = mock.MagicMock()
        result = submit_transfer(mock_transfer_client, mock_transfer_data)
        self.assertTrue(result == 'my_task_id')
        mock_alert_admins.assert_not_called()

        mock_alert_admins.reset_mock()
        mock_err_response = mock.MagicMock()
        mock_err_response.status_code = 400
        mock_err_response.headers = {}
        mock_transfer_client.submit_transfer.side_effect = TransferAPIError(mock_err_response)
        
        result = submit_transfer(mock_transfer_client, mock_transfer_data)
        self.assertIsNone(result)
        mock_alert_admins.assert_called()

    def test_add_acl(self):
        mock_transfer_client = mock.MagicMock()
        mock_response = mock.MagicMock()
        mock_response.http_status = 201
        d = {'access_id': 'rule_id'}
        mock_response.__getitem__.side_effect = d.__getitem__
        mock_transfer_client.add_endpoint_acl_rule.return_value = mock_response
        result = add_acl_rule(mock_transfer_client, '123', '/foo', 'rw')  
        self.assertEqual(result, 'rule_id') 

        mock_response.http_status = 400
        result = add_acl_rule(mock_transfer_client, '123', '/foo', 'rw')  
        self.assertIsNone(result) 

        mock_err_response = mock.MagicMock()
        mock_err_response.status_code = 400
        mock_err_response.headers = {}
        mock_transfer_client.add_endpoint_acl_rule.side_effect = TransferAPIError(mock_err_response)

        result = add_acl_rule(mock_transfer_client, '123', '/foo', 'rw')  
        self.assertIsNone(result) 

    @mock.patch('api.utilities.globus.create_application_transfer_client')
    def test_delete_acl(self, mock_create_application_transfer_client):
        mock_transfer_client = mock.MagicMock()
        mock_response = mock.MagicMock()
        mock_response.http_status = 200
        mock_transfer_client.delete_endpoint_acl_rule.return_value = mock_response
        mock_create_application_transfer_client.return_value = mock_transfer_client
        self.assertTrue(delete_acl_rule('rule_id'))

        mock_response.http_status = 400
        mock_transfer_client.delete_endpoint_acl_rule.return_value = mock_response
        mock_create_application_transfer_client.return_value = mock_transfer_client
        self.assertFalse(delete_acl_rule('rule_id'))

        mock_err_response = mock.MagicMock()
        mock_err_response.status_code = 404
        mock_err_response.headers = {}
        mock_transfer_client.delete_endpoint_acl_rule.side_effect = TransferAPIError(mock_err_response)
        mock_create_application_transfer_client.return_value = mock_transfer_client
        self.assertFalse(delete_acl_rule('rule_id'))

    @mock.patch('api.utilities.globus.alert_admins')
    def test_transfer_submission(self, mock_alert_admins):
        mock_transfer_client = mock.MagicMock()
        mock_transfer_data = mock.MagicMock()

        mock_transfer_client.submit_transfer.return_value = {'task_id': 'my_task_id'}
        result = submit_transfer(mock_transfer_client, mock_transfer_data)
        self.assertEqual(result, 'my_task_id')
        mock_alert_admins.assert_not_called()

        mock_err_response = mock.MagicMock()
        mock_err_response.status_code = 404
        mock_err_response.headers = {}
        mock_transfer_client.submit_transfer.side_effect = TransferAPIError(mock_err_response)
        result = submit_transfer(mock_transfer_client, mock_transfer_data)
        self.assertIsNone(result)
        mock_alert_admins.assert_called()

    @override_settings(GLOBUS_BUCKET=True)
    @mock.patch('api.utilities.globus.create_endpoint_manager_transfer_client')
    @mock.patch('api.utilities.globus.default_storage')
    def test_post_upload(self, 
        mock_default_storage, mock_create_endpoint_manager_transfer_client):
        mock_info = [
            {'destination_path': '/path/to/dest/f1.tsv'},
            {'destination_path': '/path/to/dest/f2.tsv'},
        ]
        # TODO: remove these workarounds once Globus creates a new release:
        response = mock.MagicMock()
        response.data = {
            'DATA': mock_info
        }

        mock_transfer_client = mock.MagicMock()
        mock_transfer_client.get.return_value = response
        # TODO: re-enable once Globus releases new version:
        #mock_transfer_client.endpoint_manager_task_successful_transfers.return_value = mock_info
        mock_create_endpoint_manager_transfer_client.return_value = mock_transfer_client
        task_id = 'abc123'
        mock_user = mock.MagicMock()
        post_upload(task_id, mock_user)
        paths = [
            f's3://{settings.GLOBUS_BUCKET}/path/to/dest/f1.tsv',
            f's3://{settings.GLOBUS_BUCKET}/path/to/dest/f2.tsv',            
        ]
        mock_default_storage.wait_until_exists.assert_has_calls([
            mock.call(paths[0]),
            mock.call(paths[1]),
        ])
        mock_default_storage.create_resource_from_interbucket_copy.has_calls(
            mock.call(mock_user, paths[0]),
            mock.call(mock_user, paths[1])
        )


class GlobusUploadTests(BaseAPITestCase):

    def setUp(self):
        self.globus_upload_url = reverse('globus-upload')
        self.establish_clients()

    @override_settings(GLOBUS_ENABLED=True, GLOBUS_ENDPOINT_ID='dest_id')
    @mock.patch('api.views.globus_views.add_acl_rule')
    @mock.patch('api.views.globus_views.submit_transfer')
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
        mock_poll_globus_task,
        mock_submit_transfer,
        mock_add_acl_rule):

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
        mock_add_acl_rule.return_value = 'some_rule_id'
        mock_user_transfer_client.get_task.return_value = {'label': mock_payload['params']['label']}
        mock_create_application_transfer_client.return_value = mock_app_transfer_client
        mock_create_user_transfer_client.return_value = mock_user_transfer_client
        mock_submit_transfer.return_value = 'my_task_id'


        headers = {'HTTP_ORIGIN': 'foo'}
        r = self.authenticated_regular_client.post(
            self.globus_upload_url, 
            data=mock_payload, 
            format='json', 
            **headers)
        j = r.json()
        self.assertTrue(j['transfer_id'] == 'my_task_id')
        mock_add_acl_rule.assert_called()
        mock_transfer_data.add_item.assert_has_calls([
            mock.call(source_path='/home/folder/f0.txt', destination_path=f'/tmp-{u}/f0.txt'),
            mock.call(source_path='/home/folder/f1.txt', destination_path=f'/tmp-{u}/f1.txt'),
        ])
        mock_user_transfer_client.endpoint_autoactivate.assert_has_calls([
            mock.call('source_id'),
            mock.call('dest_id')
        ])
        mock_submit_transfer.assert_called_with(mock_user_transfer_client, mock_transfer_data)
        mock_user_transfer_client.get_task.assert_called_with('my_task_id')
        mock_poll_globus_task.delay.assert_called_with('my_task_id', GLOBUS_UPLOAD)

        tasks = GlobusTask.objects.filter(user=self.regular_user_1)
        self.assertTrue(len(tasks) == 1)
        task = tasks[0]
        self.assertTrue(task.task_id == 'my_task_id')
        self.assertTrue(task.rule_id == 'some_rule_id')
        self.assertTrue(task.label == mock_payload['params']['label'])

    @override_settings(GLOBUS_ENABLED=True)
    @mock.patch('api.views.globus_views.alert_admins')
    @mock.patch('api.views.globus_views.add_acl_rule')
    @mock.patch('api.views.globus_views.create_application_transfer_client')
    @mock.patch('api.views.globus_views.create_user_transfer_client')
    @mock.patch('api.views.globus_views.get_globus_uuid')
    def test_acl_addition_failure_returns_500(self,
        mock_get_globus_uuid,
        mock_create_user_transfer_client, 
        mock_create_application_transfer_client,
        mock_add_acl_rule,
        mock_alert_admins):

        mock_add_acl_rule.return_value = None
        headers = {'HTTP_ORIGIN': 'foo'}
        r = self.authenticated_regular_client.post(
            self.globus_upload_url, 
            data={'params': {'label': ''}}, 
            format='json', 
            **headers)
        mock_alert_admins.assert_called()
        self.assertTrue(r.status_code == 500)

    @override_settings(GLOBUS_ENABLED=True, GLOBUS_ENDPOINT_ID='dest_id')
    @mock.patch('api.views.globus_views.add_acl_rule')
    @mock.patch('api.views.globus_views.submit_transfer')
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
        mock_poll_globus_task,
        mock_submit_transfer,
        mock_add_acl_rule):

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
        mock_add_acl_rule.return_value = 'some_rule_id'
        # If the submission fails, this function returns None, indicating
        # a failure
        mock_submit_transfer.return_value = None
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
        mock_add_acl_rule.assert_called()
        mock_transfer_data.add_item.assert_has_calls([
            mock.call(source_path='/home/folder/f0.txt', destination_path=f'/tmp-{u}/f0.txt'),
            mock.call(source_path='/home/folder/f1.txt', destination_path=f'/tmp-{u}/f1.txt'),
        ])
        mock_user_transfer_client.endpoint_autoactivate.assert_has_calls([
            mock.call('source_id'),
            mock.call('dest_id')
        ])
        mock_submit_transfer.assert_called_with(mock_user_transfer_client, mock_transfer_data)
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
    @mock.patch('api.views.globus_views.check_globus_tokens')
    @mock.patch('api.views.globus_views.get_globus_uuid')
    def test_oauth2_code_request(self, mock_get_globus_uuid, 
                                 mock_check_globus_tokens, 
                                 mock_create_or_update_token,
                                 mock_get_globus_client):
        '''
        Tests the leg of the oauth2 flow where the backend receives the code
        '''

        mock_client = mock.MagicMock()
        mock_tokens = mock.MagicMock()
        mock_tokens.by_resource_server = {'a': 1}
        mock_client.oauth2_exchange_code_for_tokens.return_value = mock_tokens
        mock_client.oauth2_get_authorize_url.return_value = 'some-auth-uri'
        mock_get_globus_client.return_value = mock_client

        # We first mock the situation where a user has tokens and 
        # a recent globus session. The high-assurance collections
        # require this.

        # by returning True, we are mocking there being valid tokens
        # and a recent Globus session
        mock_check_globus_tokens.return_value = True

        headers = {'HTTP_ORIGIN': 'foo'}
        url = f'{self.globus_init_url}?direction=upload&code=foo'
        r = self.authenticated_regular_client.get(url, **headers)
        j = r.json()
        self.assertTrue('globus-browser-url' in j)
        mock_create_or_update_token.assert_called_with(
            self.regular_user_1, {'a': 1})

        # Now mock the case where we have tokens, but the session
        # was not recent
        mock_get_globus_uuid.return_value = uuid.uuid4()
        mock_check_globus_tokens.return_value = False
        mock_create_or_update_token.reset_mock()
        headers = {'HTTP_ORIGIN': 'foo'}
        url = f'{self.globus_init_url}?direction=upload&code=foo'
        r = self.authenticated_regular_client.get(url, **headers)
        j = r.json()
        self.assertTrue('globus-auth-url' in j)
        mock_create_or_update_token.assert_called_with(
            self.regular_user_1, {'a': 1})