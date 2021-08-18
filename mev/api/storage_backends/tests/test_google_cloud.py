import unittest.mock as mock
import os

from api.tests.base import BaseAPITestCase
from api.models import Resource
from api.storage_backends.base import BaseStorageBackend
from api.storage_backends.google_cloud import GoogleBucketStorage
import google

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
        owner_uuid = self.regular_user_1.pk
        expected_basename = '{uuid}.{name}'.format(
            uuid = str(r.pk),
            name = os.path.basename(original_path)
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
        owner_uuid = self.regular_user_1.pk
        expected_basename = '{uuid}.{name}'.format(
            uuid = str(r.pk),
            name = os.path.basename(original_path)
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

    @mock.patch('api.storage_backends.google_cloud.make_local_directory')
    @mock.patch('api.storage_backends.google_cloud.os.path.exists')
    @mock.patch('api.storage_backends.google_cloud.settings')
    @mock.patch('api.storage_backends.google_cloud.storage')
    @mock.patch('api.storage_backends.google_cloud.service_account')
    def test_resource_exists_case1(self, \
        mock_service_account, \
        mock_storage, \
        mock_settings, \
        mock_exists, \
        mock_make_local_directory):
        '''
        Test the case where the object is not found since the bucket
        is not found by the google api client.
        '''
        
        os.environ['STORAGE_BUCKET_NAME'] = DUMMY_BUCKETNAME
        storage_backend = GoogleBucketStorage()

        mock_client = mock.MagicMock()
        storage_backend.storage_client = mock_client

        mock_client.get_bucket.side_effect = google.api_core.exceptions.NotFound('ack!')

        with self.assertRaises(google.api_core.exceptions.NotFound):
            storage_backend.get_bucket('foo')

        self.assertFalse(storage_backend.resource_exists('gs://foo/something.txt'))

    @mock.patch('api.storage_backends.google_cloud.make_local_directory')
    @mock.patch('api.storage_backends.google_cloud.os.path.exists')
    @mock.patch('api.storage_backends.google_cloud.settings')
    @mock.patch('api.storage_backends.google_cloud.storage')
    @mock.patch('api.storage_backends.google_cloud.service_account')
    def test_resource_exists_case2(self, \
        mock_service_account, \
        mock_storage, \
        mock_settings, \
        mock_exists, \
        mock_make_local_directory):
        '''
        Tests the case where we don't have access to the object
        in the bucket since the bucket permissions block our access.
        Note, however, that you can encounter situations where the bucket
        access is blocked, but the actual object IS public. We handle
        that case elsewhere.
        '''
        
        os.environ['STORAGE_BUCKET_NAME'] = DUMMY_BUCKETNAME
        storage_backend = GoogleBucketStorage()

        mock_client = mock.MagicMock()
        storage_backend.storage_client = mock_client

        mock_client.get_bucket.side_effect = google.api_core.exceptions.Forbidden('ack!')

        with self.assertRaises(google.api_core.exceptions.Forbidden):
            storage_backend.get_bucket('foo')
        self.assertFalse(storage_backend.resource_exists('gs://foo/something.txt'))

    @mock.patch('api.storage_backends.google_cloud.make_local_directory')
    @mock.patch('api.storage_backends.google_cloud.os.path.exists')
    @mock.patch('api.storage_backends.google_cloud.settings')
    @mock.patch('api.storage_backends.google_cloud.storage')
    @mock.patch('api.storage_backends.google_cloud.service_account')
    def test_resource_exists_case3(self, \
        mock_service_account, \
        mock_storage, \
        mock_settings, \
        mock_exists, \
        mock_make_local_directory):
        '''
        This mocks out the get_blob method so that it returns
        something that is not None
        '''
        
        os.environ['STORAGE_BUCKET_NAME'] = DUMMY_BUCKETNAME
        storage_backend = GoogleBucketStorage()

        mock_client = mock.MagicMock()
        storage_backend.storage_client = mock_client

        mock_blob = mock.MagicMock()
        mock_get_blob = mock.MagicMock()
        mock_get_blob.return_value = mock_blob
        storage_backend.get_blob = mock_get_blob
        self.assertTrue(storage_backend.resource_exists('gs://foo/something.txt'))

    @mock.patch('api.storage_backends.google_cloud.make_local_directory')
    @mock.patch('api.storage_backends.google_cloud.os.path.exists')
    @mock.patch('api.storage_backends.google_cloud.settings')
    @mock.patch('api.storage_backends.google_cloud.storage')
    @mock.patch('api.storage_backends.google_cloud.service_account')
    def test_resource_exists_case4(self, \
        mock_service_account, \
        mock_storage, \
        mock_settings, \
        mock_exists, \
        mock_make_local_directory):
        '''
        This mocks out the get_blob method so that it returns
        None ()
        '''
        
        os.environ['STORAGE_BUCKET_NAME'] = DUMMY_BUCKETNAME
        storage_backend = GoogleBucketStorage()

        mock_client = mock.MagicMock()
        storage_backend.storage_client = mock_client

        mock_get_blob = mock.MagicMock()
        mock_get_blob.return_value = None
        storage_backend.get_blob = mock_get_blob
        self.assertFalse(storage_backend.resource_exists('gs://foo/something.txt'))

    @mock.patch('api.storage_backends.google_cloud.make_local_directory')
    @mock.patch('api.storage_backends.google_cloud.os.path.exists')
    @mock.patch('api.storage_backends.google_cloud.settings')
    @mock.patch('api.storage_backends.google_cloud.storage')
    @mock.patch('api.storage_backends.google_cloud.service_account')
    def test_resource_exists_case5(self, \
        mock_service_account, \
        mock_storage, \
        mock_settings, \
        mock_exists, \
        mock_make_local_directory):
        '''
        Here we mock that *something* raised an exception in the process of getting
        either the bucket or the object. Hence, the get_blob method will raise an ex
        and we check that the existence method returns False appropriately.
        '''
        
        os.environ['STORAGE_BUCKET_NAME'] = DUMMY_BUCKETNAME
        storage_backend = GoogleBucketStorage()

        mock_client = mock.MagicMock()
        storage_backend.storage_client = mock_client

        mock_get_blob = mock.MagicMock()
        mock_get_blob.side_effect = Exception('ack')
        storage_backend.get_blob = mock_get_blob
        self.assertFalse(storage_backend.resource_exists('gs://foo/something.txt'))