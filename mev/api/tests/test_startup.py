import unittest
import unittest.mock as mock

from django.core.exceptions import ImproperlyConfigured
from django.conf import settings

from api.cloud_backends.google_cloud import startup_check

'''
This set of tests checks that the startup checks execute as planned.
Namely, ensures that the proper errors are emitted if there is a failure
in getting things properly configured.
'''

class GoogleCloudStartupTest(unittest.TestCase):

    @mock.patch('api.cloud_backends.google_cloud.get_runner')
    @mock.patch('api.cloud_backends.google_cloud.get_instance_region')
    @mock.patch('api.cloud_backends.google_cloud.settings')
    @mock.patch('api.storage_backends.google_cloud.GoogleBucketStorage.get_bucket')
    @mock.patch('api.storage_backends.google_cloud.storage')
    @mock.patch('api.storage_backends.google_cloud.service_account')
    @mock.patch('api.storage_backends.google_cloud.settings')
    def test_google_cloud_case1(self, \
        mock_storage_settings, \
        mock_storage_service_account, \
        mock_storage, \
        mock_get_bucket, \
        mock_settings, \
        mock_get_instance_region, \
        mock_get_runner):
        '''
        Here we simulate the case where everything is good to go
        and consistent when using bucket storage and remote job runners
        '''
        mock_get_instance_region.return_value = 'foo-region'
        mock_settings.ENABLE_REMOTE_JOBS = True
        mock_settings.REQUESTED_REMOTE_JOB_RUNNERS = ['abc',]
        mock_settings.STORAGE_LOCATION = settings.REMOTE
        mock_runner_class = mock.MagicMock()
        mock_runner = mock.MagicMock()
        mock_runner.check_if_ready.return_value = None
        mock_runner_class.return_value = mock_runner
        mock_get_runner.return_value = mock_runner_class
        mock_bucket = mock.MagicMock()
        mock_bucket.location = 'foo-region'
        mock_get_bucket.return_value = mock_bucket
        startup_check()
        mock_runner.check_if_ready.assert_called()


    @mock.patch('api.cloud_backends.google_cloud.get_runner')
    @mock.patch('api.cloud_backends.google_cloud.get_instance_region')
    @mock.patch('api.cloud_backends.google_cloud.settings')
    @mock.patch('api.storage_backends.google_cloud.GoogleBucketStorage.get_bucket')
    @mock.patch('api.storage_backends.google_cloud.storage')
    @mock.patch('api.storage_backends.google_cloud.service_account')
    @mock.patch('api.storage_backends.google_cloud.settings')
    def test_google_cloud_case2(self, 
        mock_storage_settings,
        mock_storage_service_account,
        mock_storage,
        mock_get_bucket, 
        mock_settings, 
        mock_get_instance_region, 
        mock_get_runner):
        '''
        Here we simulate the case where bucket-storage is used, but the bucket
        is in a different region than the VM running the instance. We want to 
        fail that.
        '''
        mock_get_instance_region.return_value = 'foo-region'
        mock_settings.ENABLE_REMOTE_JOBS = True
        mock_settings.REQUESTED_REMOTE_JOB_RUNNERS = ['abc',]
        mock_settings.STORAGE_LOCATION = settings.REMOTE
        mock_runner_class = mock.MagicMock()
        mock_runner = mock.MagicMock()
        mock_runner.check_if_ready.return_value = None
        mock_runner_class.return_value = mock_runner
        mock_get_runner.return_value = mock_runner_class
        mock_bucket = mock.MagicMock()
        mock_bucket.location = 'other-region'
        mock_get_bucket.return_value = mock_bucket

        with self.assertRaises(ImproperlyConfigured):
            startup_check()
        mock_runner.check_if_ready.assert_called()

    @mock.patch('api.cloud_backends.google_cloud.get_runner')
    @mock.patch('api.cloud_backends.google_cloud.get_with_retry')
    @mock.patch('api.cloud_backends.google_cloud.get_instance_region')
    @mock.patch('api.cloud_backends.google_cloud.settings')
    @mock.patch('api.storage_backends.google_cloud.GoogleBucketStorage.get_bucket')
    @mock.patch('api.storage_backends.google_cloud.storage')
    @mock.patch('api.storage_backends.google_cloud.service_account')
    @mock.patch('api.storage_backends.google_cloud.settings')
    def test_google_cloud_case3(self, 
        mock_storage_settings,
        mock_storage_service_account,
        mock_storage, 
        mock_get_bucket, 
        mock_settings, 
        mock_get_instance_region, 
        mock_get_with_retry, 
        mock_get_runner):
        '''
        Simulate the case where bucket-storage is used but we do NOT enable
        remote job runners
        '''
        mock_get_instance_region.return_value = 'foo-region'
        mock_settings.ENABLE_REMOTE_JOBS = False
        mock_settings.STORAGE_LOCATION = settings.REMOTE
        mock_runner_class = mock.MagicMock()
        mock_runner = mock.MagicMock()
        mock_runner.check_if_ready.return_value = None
        mock_runner_class.return_value = mock_runner
        mock_get_runner.return_value = mock_runner_class
        mock_bucket = mock.MagicMock()
        mock_bucket.location = 'foo-region'
        mock_get_bucket.return_value = mock_bucket
        startup_check()