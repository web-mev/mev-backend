import unittest.mock as mock
import os

from api.storage_backends import LocalStorage, GoogleBucketStorage
from api.storage_backends.helpers import get_storage_implementation

from api.tests.base import BaseAPITestCase

class TestStorageHelpers(BaseAPITestCase):

    @mock.patch('api.storage_backends.google_cloud.storage')
    @mock.patch('api.storage_backends.google_cloud.service_account')
    @mock.patch('api.storage_backends.google_cloud.settings')
    def test_get_storage_impl(self, mock_settings, mock_service_account, mock_storage):
        '''
        Tests that we get back the proper storage backend given a file path.
        Note that this is more general than the choice provided for the storage
        backend (which is chosen as part of the application startup). Instead,
        this function infers the storage resource based on the path (e.g. paths
        that start with "gs:" mean we have a file in Google bucket storage)
        ''' 
        path = 'gs://foo-bucket/bar/object.txt'
        c = get_storage_implementation(path)
        self.assertEqual(type(c), GoogleBucketStorage)
        mock_storage.Client.assert_called()

        path = 'foo.txt'
        c = get_storage_implementation(path)
        self.assertEqual(type(c), LocalStorage)

        path = '/root/foo.txt'
        c = get_storage_implementation(path)
        self.assertEqual(type(c), LocalStorage)

        path = 's3://foo.txt'
        with self.assertRaises(Exception):
            get_storage_implementation(path)
