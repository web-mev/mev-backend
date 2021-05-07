import unittest.mock as mock
import os

from api.tests.base import BaseAPITestCase
from api.models import Resource
from api.storage_backends.base import BaseStorageBackend
from api.storage_backends.google_cloud import GoogleBucketStorage

DUMMY_BUCKETNAME = 'a-google-bucket'

class TestGoogleBucketStorage(BaseAPITestCase):

    def setUp(self):
        self.establish_clients()

    @mock.patch('api.storage_backends.google_cloud.os.path.exists')
    @mock.patch('api.storage_backends.google_cloud.storage')
    @mock.patch('api.storage_backends.google_cloud.service_account')
    @mock.patch('api.storage_backends.google_cloud.settings')
    def test_resource_path_altered_correctly(self, 
        mock_settings,
        mock_service_account, 
        mock_storage, 
        mock_os_exists):

        resources = Resource.objects.filter(owner=self.regular_user_1)
        r = resources[0]
        original_path = r.path
        filename = r.name
        owner_uuid = self.regular_user_1.pk
        expected_basename = '{uuid}.{name}'.format(
            uuid = str(r.pk),
            name = filename
        )

        os.environ['STORAGE_BUCKET_NAME'] = DUMMY_BUCKETNAME
        storage_backend = GoogleBucketStorage()
        mock_bucket = mock.MagicMock()
        mock_upload_blob = mock.MagicMock()
        storage_backend.get_or_create_bucket = mock.MagicMock()
        storage_backend.get_or_create_bucket.return_value = mock_bucket
        storage_backend.upload_blob = mock_upload_blob
        path = storage_backend.store(r)

        mock_os_exists.return_value = True

        mock_upload_blob.assert_called()
        storage_backend.get_or_create_bucket.assert_called()
        expected_destination = os.path.join( GoogleBucketStorage.BUCKET_PREFIX, \
            DUMMY_BUCKETNAME, \
            Resource.USER_RESOURCE_STORAGE_DIRNAME, \
            str(owner_uuid), expected_basename)
        self.assertEqual(path, expected_destination)

    @mock.patch('api.storage_backends.google_cloud.os.path.exists')
    @mock.patch('api.storage_backends.google_cloud.storage')
    @mock.patch('api.storage_backends.google_cloud.service_account')
    @mock.patch('api.storage_backends.google_cloud.settings')
    def test_bucket_transfer_call(self, 
        mock_settings, 
        mock_service_account, 
        mock_storage, mock_os_exists):
        '''
        If an analysis is performed remotely (so that files are located in 
        bucket storage) and the storage backend is also bucket-based, we need to 
        perform an inter-bucket transfer. Test that the proper calls are made
        '''
        resources = Resource.objects.filter(owner=self.regular_user_1)
        r = resources[0]
        original_path = r.path
        filename = r.name
        owner_uuid = self.regular_user_1.pk
        expected_basename = '{uuid}.{name}'.format(
            uuid = str(r.pk),
            name = filename
        )

        os.environ['STORAGE_BUCKET_NAME'] = DUMMY_BUCKETNAME
        mock_settings.STORAGE_CREDENTIALS = '/some/dummy/path'
        storage_backend = GoogleBucketStorage()
        mock_bucket = mock.MagicMock()
        mock_upload_blob = mock.MagicMock()
        mock_interbucket_transfer = mock.MagicMock()
        storage_backend.get_or_create_bucket = mock.MagicMock()
        storage_backend.get_or_create_bucket.return_value = mock_bucket
        storage_backend.upload_blob = mock_upload_blob
        storage_backend.perform_interbucket_transfer = mock_interbucket_transfer

        # If this is False, then the Resource does not exist on the local filesystem.
        # This is what triggers the alternative behavior of performing an interbucket
        # transfer
        mock_os_exists.return_value = False

        path = storage_backend.store(r)

        mock_upload_blob.assert_not_called()
        mock_interbucket_transfer.assert_called()
        storage_backend.get_or_create_bucket.assert_called()
        expected_destination = os.path.join( GoogleBucketStorage.BUCKET_PREFIX, \
            DUMMY_BUCKETNAME, \
            Resource.USER_RESOURCE_STORAGE_DIRNAME, \
            str(owner_uuid), expected_basename)
        self.assertEqual(path, expected_destination)

    @mock.patch('api.storage_backends.google_cloud.make_local_directory')
    @mock.patch('api.storage_backends.google_cloud.os.path.exists')
    @mock.patch('api.storage_backends.google_cloud.settings')
    @mock.patch('api.storage_backends.google_cloud.storage')
    @mock.patch('api.storage_backends.google_cloud.service_account')
    def test_local_resource_pull_case1(self, \
        mock_service_account, \
        mock_storage, \
        mock_settings, \
        mock_exists, \
        mock_make_local_directory):
        '''
        To validate files, we need them locally.  This tests that the 
        `get_local_resource_path` performs the proper calls if the resource
        is not in our local cache.  Also checks that the local user cache
        directory is created (via mock)
        '''
        resources = Resource.objects.filter(owner=self.regular_user_1)
        r = resources[0]
        relative_path = BaseStorageBackend.construct_relative_path(r)

        cache_dir = '/some/cache/dir'
        mock_settings.RESOURCE_CACHE_DIR = cache_dir

        mock_exists.return_value = False

        os.environ['STORAGE_BUCKET_NAME'] = DUMMY_BUCKETNAME
        storage_backend = GoogleBucketStorage()
        mock_get_blob = mock.MagicMock()
        mock_blob = mock.MagicMock()
        mock_get_blob.return_value = mock_blob
        storage_backend.get_blob = mock_get_blob

        expected_final_location = os.path.join(cache_dir, relative_path)

        location = storage_backend.get_local_resource_path(r)

        mock_blob.download_to_filename.assert_called()
        mock_make_local_directory.assert_called_with(os.path.dirname(location))
        self.assertEqual(location, expected_final_location)

    @mock.patch('api.storage_backends.google_cloud.make_local_directory')
    @mock.patch('api.storage_backends.google_cloud.os.path.exists')
    @mock.patch('api.storage_backends.google_cloud.settings')
    @mock.patch('api.storage_backends.google_cloud.storage')
    @mock.patch('api.storage_backends.google_cloud.service_account')
    def test_local_resource_pull_case2(self, \
        mock_service_account, \
        mock_storage, \
        mock_settings, \
        mock_exists, \
        mock_make_local_directory):
        '''
        To validate files, we need them locally.  This tests that the 
        `get_local_resource_path` performs the proper calls if the resource
        is not in our local cache.  In this case, the user's local cache
        directory already exists.
        '''
        resources = Resource.objects.filter(owner=self.regular_user_1)
        r = resources[0]
        relative_path = BaseStorageBackend.construct_relative_path(r)

        cache_dir = '/some/cache/dir'
        mock_settings.RESOURCE_CACHE_DIR = cache_dir

        mock_exists.side_effect = [True, False]

        os.environ['STORAGE_BUCKET_NAME'] = DUMMY_BUCKETNAME
        storage_backend = GoogleBucketStorage()
        mock_get_blob = mock.MagicMock()
        mock_blob = mock.MagicMock()
        mock_blob.download_to_filename.side_effect = [None,]
        mock_get_blob.return_value = mock_blob
        storage_backend.get_blob = mock_get_blob

        expected_final_location = os.path.join(cache_dir, relative_path)

        location = storage_backend.get_local_resource_path(r)
        self.assertEqual(1,mock_blob.download_to_filename.call_count)
        mock_make_local_directory.assert_not_called()
        self.assertEqual(location, expected_final_location)

    @mock.patch('api.storage_backends.google_cloud.make_local_directory')
    @mock.patch('api.storage_backends.google_cloud.os.path.exists')
    @mock.patch('api.storage_backends.google_cloud.settings')
    @mock.patch('api.storage_backends.google_cloud.storage')
    @mock.patch('api.storage_backends.google_cloud.service_account')
    def test_local_resource_pull_case3(self, \
        mock_service_account, \
        mock_storage, \
        mock_settings, \
        mock_exists, \
        mock_make_local_directory):
        '''
        To validate files, we need them locally.  This tests that the 
        `get_local_resource_path` performs the proper calls if the resource
        is, in fact, already in the local cache
        '''
        resources = Resource.objects.filter(owner=self.regular_user_1)
        r = resources[0]
        relative_path = BaseStorageBackend.construct_relative_path(r)

        cache_dir = '/some/cache/dir'
        mock_settings.RESOURCE_CACHE_DIR = cache_dir

        mock_exists.side_effect = [True, True]

        os.environ['STORAGE_BUCKET_NAME'] = DUMMY_BUCKETNAME
        storage_backend = GoogleBucketStorage()
        mock_get_blob = mock.MagicMock()
        mock_blob = mock.MagicMock()
        mock_get_blob.return_value = mock_blob
        storage_backend.get_blob = mock_get_blob

        expected_final_location = os.path.join(cache_dir, relative_path)

        location = storage_backend.get_local_resource_path(r)

        mock_blob.download_to_filename.assert_not_called()
        mock_make_local_directory.assert_not_called()
        self.assertEqual(location, expected_final_location)

    @mock.patch('api.storage_backends.google_cloud.make_local_directory')
    @mock.patch('api.storage_backends.google_cloud.os.path.exists')
    @mock.patch('api.storage_backends.google_cloud.settings')
    @mock.patch('api.storage_backends.google_cloud.storage')
    @mock.patch('api.storage_backends.google_cloud.service_account')
    def test_local_resource_pull_retry(self, \
        mock_service_account, \
        mock_storage, \
        mock_settings, \
        mock_exists, \
        mock_make_local_directory):
        '''
        To validate files, we need them locally.  This tests that the 
        `get_local_resource_path` performs the proper calls if the resource
        is not in our local cache.  Also checks that the local user cache
        directory is created (via mock)
        '''
        resources = Resource.objects.filter(owner=self.regular_user_1)
        r = resources[0]
        relative_path = BaseStorageBackend.construct_relative_path(r)

        cache_dir = '/some/cache/dir'
        mock_settings.RESOURCE_CACHE_DIR = cache_dir

        mock_exists.return_value = False

        os.environ['STORAGE_BUCKET_NAME'] = DUMMY_BUCKETNAME
        storage_backend = GoogleBucketStorage()
        mock_get_blob = mock.MagicMock()
        mock_blob = mock.MagicMock()
        mock_blob.download_to_filename.side_effect = [Exception('Something bad'), None]
        mock_get_blob.return_value = mock_blob
        storage_backend.get_blob = mock_get_blob

        expected_final_location = os.path.join(cache_dir, relative_path)

        location = storage_backend.get_local_resource_path(r)

        self.assertEqual(2,mock_blob.download_to_filename.call_count)
        mock_make_local_directory.assert_called_with(os.path.dirname(location))
        self.assertEqual(location, expected_final_location)