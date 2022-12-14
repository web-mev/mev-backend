import uuid
import unittest.mock as mock

from django.urls import reverse
from rest_framework import status

from api.tests.base import BaseAPITestCase


class LocalDropboxUploadTests(BaseAPITestCase):

    def setUp(self):
        self.url = reverse('dropbox-upload')
        self.establish_clients()

    @mock.patch('api.views.resource_upload_views.get_async_uploader')
    @mock.patch('api.views.resource_upload_views.submit_async_job')    
    @mock.patch('api.views.resource_upload_views.uuid')
    def test_job_called(self, mock_uuid, mock_submit_async_job, mock_get_async_uploader):
        u1 = uuid.uuid4()
        mock_uuid.uuid4.side_effect = [u1,]
        mock_dropbox_uploader = mock.MagicMock()
        item = {
            'dropbox_links': ['a','b'],
            'filenames': ['c','d']
        }
        mock_dropbox_uploader.rename_inputs.return_value = [item,]
        mock_op_id = 'abc'
        mock_dropbox_uploader.op_id = mock_op_id
        mock_get_async_uploader.return_value = mock_dropbox_uploader
        payload1 = {
            'download_link': 'https://dropbox-url.com/foo',
            'filename': 'abc'
        }
        payload2 = {
            'download_link': 'https://dropbox-url.com/bar',
            'filename': 'xyz'
        }
        response = self.authenticated_regular_client.post(
            self.url, 
            data=[payload1, payload2],
            format='json'
        )
        self.assertTrue(mock_submit_async_job.delay.call_count == 1)
        mock_submit_async_job.delay.assert_has_calls([
            mock.call(
                u1, mock_op_id, self.regular_user_1.pk, None,str(u1), item
            )
        ])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        j = response.json()
        self.assertTrue(len(j['upload_ids']) == 1)
        self.assertEqual(j['upload_ids'][0], str(u1))


class AWSRemoteDropboxUploadTests(BaseAPITestCase):
    def setUp(self):
        self.url = reverse('dropbox-upload')
        self.establish_clients()

    @mock.patch('api.views.resource_upload_views.get_async_uploader')
    @mock.patch('api.views.resource_upload_views.submit_async_job')
    @mock.patch('api.views.resource_upload_views.uuid')
    def test_multiple_jobs_called(self, mock_uuid, mock_submit_async_job, mock_get_async_uploader):

        u1 = uuid.uuid4()
        u2 = uuid.uuid4()
        mock_uuid.uuid4.side_effect = [u1, u2]
        mock_dropbox_uploader = mock.MagicMock()
        item1 = {
            'AWSDropboxUpload.dropbox_link': 'l1',
            'AWSDropboxUpload.filename': 'f1',
            'AWSDropboxUpload.bucketname': 'x',
            'AWSDropboxUpload.storage_root': 'y'  
        }
        item2 = {
            'AWSDropboxUpload.dropbox_link': 'l2',
            'AWSDropboxUpload.filename': 'f2',
            'AWSDropboxUpload.bucketname': 'x',
            'AWSDropboxUpload.storage_root': 'y'  
        }
        mock_op_id = 'abc'
        mock_dropbox_uploader.op_id = mock_op_id
        mock_dropbox_uploader.rename_inputs.return_value = [item1, item2]
        mock_get_async_uploader.return_value = mock_dropbox_uploader
        payload1 = {
            'download_link': 'https://dropbox-url.com/foo',
            'filename': 'abc'
        }
        payload2 = {
            'download_link': 'https://dropbox-url.com/bar',
            'filename': 'xyz'
        }
        response = self.authenticated_regular_client.post(
            self.url, 
            data=[payload1, payload2],
            format='json'
        )
        self.assertTrue(mock_submit_async_job.delay.call_count == 2)
        mock_submit_async_job.delay.assert_has_calls([
            mock.call(
                u1, mock_op_id, self.regular_user_1.pk, None,str(u1), item1
            ),
            mock.call(
                u2, mock_op_id, self.regular_user_1.pk, None,str(u2), item2
            )
        ])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        j = response.json()
        self.assertTrue(len(j['upload_ids']) == 2)
        self.assertCountEqual(j['upload_ids'], [str(u1), str(u2)])
