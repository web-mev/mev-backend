import unittest.mock as mock
import os

from api.tests.base import BaseAPITestCase
from api.models import Resource
from api.storage_backends.base import BaseStorageBackend
from api.storage_backends.google_cloud import GoogleBucketStorage, \
    BUCKET_PREFIX

DUMMY_BUCKETNAME = 'a-google-bucket'

class TestGoogleBucketStorage(BaseAPITestCase):

    def setUp(self):
        self.establish_clients()

    @mock.patch('api.storage_backends.google_cloud.storage')
    @mock.patch('api.storage_backends.google_cloud.GOOGLE_BUCKET_NAME', DUMMY_BUCKETNAME)
    def test_resource_path_altered_correctly(self, mock_storage):

        resources = Resource.objects.filter(owner=self.regular_user_1)
        r = resources[0]
        original_path = r.path
        filename = r.name
        owner_uuid = self.regular_user_1.pk
        expected_basename = '{uuid}.{name}'.format(
            uuid = str(r.pk),
            name = filename
        )
        expected_destination = os.path.join( BUCKET_PREFIX, \
            DUMMY_BUCKETNAME, str(owner_uuid), expected_basename)

        storage_backend = GoogleBucketStorage()
        mock_bucket = mock.MagicMock()
        mock_upload_blob = mock.MagicMock()
        storage_backend.get_or_create_bucket = mock.MagicMock()
        storage_backend.get_or_create_bucket.return_value = mock_bucket
        storage_backend.upload_blob = mock_upload_blob
        path = storage_backend.store(r)

        mock_upload_blob.assert_called()
        storage_backend.get_or_create_bucket.assert_called()
        self.assertEqual(path, expected_destination)

    @mock.patch('api.storage_backends.google_cloud.make_local_directory')
    @mock.patch('api.storage_backends.google_cloud.os.path.exists')
    @mock.patch('api.storage_backends.google_cloud.settings')
    @mock.patch('api.storage_backends.google_cloud.storage')
    @mock.patch('api.storage_backends.google_cloud.GOOGLE_BUCKET_NAME', DUMMY_BUCKETNAME)
    def test_local_resource_pull_case1(self, \
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
    @mock.patch('api.storage_backends.google_cloud.GOOGLE_BUCKET_NAME', DUMMY_BUCKETNAME)
    def test_local_resource_pull_case2(self, \
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

        storage_backend = GoogleBucketStorage()
        mock_get_blob = mock.MagicMock()
        mock_blob = mock.MagicMock()
        mock_get_blob.return_value = mock_blob
        storage_backend.get_blob = mock_get_blob

        expected_final_location = os.path.join(cache_dir, relative_path)

        location = storage_backend.get_local_resource_path(r)

        mock_blob.download_to_filename.assert_called()
        mock_make_local_directory.assert_not_called()
        self.assertEqual(location, expected_final_location)

    @mock.patch('api.storage_backends.google_cloud.make_local_directory')
    @mock.patch('api.storage_backends.google_cloud.os.path.exists')
    @mock.patch('api.storage_backends.google_cloud.settings')
    @mock.patch('api.storage_backends.google_cloud.storage')
    @mock.patch('api.storage_backends.google_cloud.GOOGLE_BUCKET_NAME', DUMMY_BUCKETNAME)
    def test_local_resource_pull_case3(self, \
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