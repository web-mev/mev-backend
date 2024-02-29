import os
import shutil
import unittest
import unittest.mock as mock

from django.conf import settings

from api.storage import S3ResourceStorage, \
    LocalResourceStorage
from botocore.exceptions import ClientError


class TestLocalResourceStorage(unittest.TestCase):

    @mock.patch('api.storage.os')
    def test_existence_method(self, mock_os):
        '''
        This is not so much a test per se as a double-check
        that our storage interface matches between the local
        and remote storage classes.
        '''
        storage = LocalResourceStorage()
        storage.check_if_exists('abc')
        mock_os.path.exists.assert_called_with('abc')


class TestS3ResourceStorage(unittest.TestCase):
    '''
    Tests the overridden methods functions of the S3ResourceStorage class.

    Note that most methods are thin wrappers on Django Storage's S3boto3Storage
    so we are not aiming to re-test that package. Rather just testing that
    the proper calls are made to that api.
    '''

    @mock.patch('api.storage.boto3')
    @mock.patch('api.storage.S3Boto3Storage.exists')
    def test_existence_in_main_storage(self, mock_base_exists, mock_boto):
        '''
        Tests that our `check_if_exists` makes the proper calls
        and handles unexpected situations properly
        '''
        storage = S3ResourceStorage()
        mock_get_bucket_and_object_from_full_path = mock.MagicMock()
        mock_bucket_name = 'my-bucket'
        mock_object_name = 'some/object.txt'
        mock_get_bucket_and_object_from_full_path.return_value = (mock_bucket_name, mock_object_name)
        storage.get_bucket_and_object_from_full_path = mock_get_bucket_and_object_from_full_path

        # check that we call the parent method if we are checking a file in
        # the "main" Django storage bucket
        storage.bucket_name = mock_bucket_name
        storage.check_if_exists(f's3://{mock_bucket_name}/{mock_object_name}')
        mock_base_exists.assert_called_once_with(mock_object_name)

    @mock.patch('api.storage.boto3')
    @mock.patch('api.storage.S3Boto3Storage.exists')
    def test_existence_in_other_storage(self, mock_base_exists, mock_boto):
        '''
        Tests that our `check_if_exists` makes the proper calls
        and handles unexpected situations properly
        '''
        storage = S3ResourceStorage()
        mock_get_bucket_and_object_from_full_path = mock.MagicMock()
        # test if we are checking an object in another bucket
        mock_other_bucket_name = 'other-bucket'
        mock_object_name = 'some/object.txt'
        mock_get_bucket_and_object_from_full_path.return_value = (mock_other_bucket_name, mock_object_name)
        mock_s3 = mock.MagicMock()
        mock_s3_object = mock.MagicMock()
        mock_s3.Object.return_value = mock_s3_object
        mock_boto.resource.return_value = mock_s3
        storage.check_if_exists(f's3://{mock_other_bucket_name}/{mock_object_name}')
        mock_s3.Object.assert_called_once_with(mock_other_bucket_name, mock_object_name)
        mock_s3_object.load.assert_called()

    @mock.patch('api.storage.alert_admins')
    @mock.patch('api.storage.boto3')
    @mock.patch('api.storage.S3Boto3Storage.exists')
    def test_existence_not_found_in_storage(self, 
            mock_base_exists,
            mock_boto,
            mock_alert_admins):
        '''
        Tests that our `check_if_exists` handles an unexpected exception
        '''
        storage = S3ResourceStorage()
        mock_get_bucket_and_object_from_full_path = mock.MagicMock()
        # test if we are checking an object in another bucket
        mock_other_bucket_name = 'other-bucket'
        mock_object_name = 'some/object.txt'
        # test that it was not found (404 response)
        mock_other_bucket_name = 'other-bucket'
        mock_get_bucket_and_object_from_full_path.return_value = (mock_other_bucket_name, mock_object_name)
        mock_s3 = mock.MagicMock()
        mock_s3_object = mock.MagicMock()
        mock_s3_object.load.side_effect = ClientError(
            {'Error': {'Code': 404, 'Message': 'abc'}},
            'load_object'
        )
        mock_s3.Object.return_value = mock_s3_object
        mock_boto.resource.return_value = mock_s3
        was_found = storage.check_if_exists(f's3://{mock_other_bucket_name}/{mock_object_name}')
        self.assertFalse(was_found)
        mock_s3.Object.assert_called_once_with(mock_other_bucket_name, mock_object_name)
        mock_s3_object.load.assert_called()
        mock_alert_admins.assert_not_called()

    @mock.patch('api.storage.alert_admins')
    @mock.patch('api.storage.boto3')
    @mock.patch('api.storage.S3Boto3Storage.exists')
    def test_non_404_response_in_storage(self,
            mock_base_exists,
            mock_boto,
            mock_alert_admins):
        '''
        Tests that our `check_if_exists` handles an unexpected exception
        '''
        storage = S3ResourceStorage()
        mock_get_bucket_and_object_from_full_path = mock.MagicMock()
        # test if we are checking an object in another bucket
        mock_other_bucket_name = 'other-bucket'
        mock_object_name = 'some/object.txt'
        # test that it was not found (404 response)
        mock_other_bucket_name = 'other-bucket'
        mock_get_bucket_and_object_from_full_path.return_value = (mock_other_bucket_name, mock_object_name)
        mock_s3 = mock.MagicMock()
        mock_s3_object = mock.MagicMock()
        mock_s3_object.load.side_effect = ClientError(
            {'Error': {'Code': 500, 'Message': 'abc'}},
            'load_object'
        )
        mock_s3.Object.return_value = mock_s3_object
        mock_boto.resource.return_value = mock_s3
        was_found = storage.check_if_exists(f's3://{mock_other_bucket_name}/{mock_object_name}')
        self.assertFalse(was_found)
        mock_s3.Object.assert_called_once_with(mock_other_bucket_name, mock_object_name)
        mock_s3_object.load.assert_called()
        mock_alert_admins.assert_called()

    @mock.patch('api.storage.alert_admins')
    @mock.patch('api.storage.boto3')
    @mock.patch('api.storage.S3Boto3Storage.exists')
    def test_existence_raises_ex(self,
            mock_base_exists,
            mock_boto,
            mock_alert_admins):
        '''
        Tests that our `check_if_exists` handles an unexpected exception
        '''
        storage = S3ResourceStorage()
        mock_get_bucket_and_object_from_full_path = mock.MagicMock()
        # test if we are checking an object in another bucket
        mock_other_bucket_name = 'other-bucket'
        mock_object_name = 'some/object.txt'
        # test that it was not found (404 response)
        mock_other_bucket_name = 'other-bucket'
        mock_get_bucket_and_object_from_full_path.return_value = (mock_other_bucket_name, mock_object_name)
        mock_s3 = mock.MagicMock()
        mock_s3_object = mock.MagicMock()
        mock_s3_object.load.side_effect = Exception('!!!')
        mock_s3.Object.return_value = mock_s3_object
        mock_boto.resource.return_value = mock_s3
        was_found = storage.check_if_exists(f's3://{mock_other_bucket_name}/{mock_object_name}')
        self.assertFalse(was_found)
        mock_s3.Object.assert_called_once_with(mock_other_bucket_name, mock_object_name)
        mock_s3_object.load.assert_called()
        mock_alert_admins.assert_called()