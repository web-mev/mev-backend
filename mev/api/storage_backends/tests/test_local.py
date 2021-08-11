import unittest.mock as mock
import os

from api.tests.base import BaseAPITestCase
from api.models import Resource
from api.storage_backends.local import LocalStorage

DUMMY_DIRNAME = 'resource_storage'

class TestLocalStorage(BaseAPITestCase):

    def setUp(self):
        self.establish_clients()

    @mock.patch('api.storage_backends.local.os.path.exists')
    @mock.patch('api.storage_backends.local.move_resource')
    @mock.patch('api.storage_backends.local.make_local_directory')
    @mock.patch('api.storage_backends.local.settings')
    @mock.patch('api.storage_backends.local.STORAGE_DIRNAME', DUMMY_DIRNAME)
    def test_resource_path_altered_correctly(self, \
        mock_settings, \
        mock_make_local_dir, \
        mock_move,
        mock_os_exists):
        '''
        Tests the case where a file is moved locally-- all within the 
        local fileystem
        '''

        base_dir = '/foo'
        mock_settings.DATA_DIR = base_dir

        resources = Resource.objects.filter(owner=self.regular_user_1)
        r = resources[0]
        original_path = r.path
        filename = r.name
        owner_uuid = self.regular_user_1.pk
        expected_basename = '{uuid}.{name}'.format(
            uuid = str(r.pk),
            name = filename
        )
        expected_destination = os.path.join(base_dir, \
            DUMMY_DIRNAME,\
            Resource.USER_RESOURCE_STORAGE_DIRNAME, \
            str(owner_uuid), expected_basename)
        mock_os_exists.return_value = True

        storage_backend = LocalStorage()
        path = storage_backend.store(r)

        self.assertEqual(path, expected_destination)
        mock_move.assert_called_with(original_path, expected_destination)
        

    @mock.patch('api.storage_backends.local.os.path.exists')
    @mock.patch('api.storage_backends.local.localize_remote_resource')
    @mock.patch('api.storage_backends.local.make_local_directory')
    @mock.patch('api.storage_backends.local.settings')
    @mock.patch('api.storage_backends.local.STORAGE_DIRNAME', DUMMY_DIRNAME)
    def test_call_to_localize_remote_resource(self, \
        mock_settings, \
        mock_make_local_dir, \
        mock_localize_remote_resource,
        mock_os_exists):
        '''
        Tests the case where a file is remote, such as when completing a cloud-based job.
        If the storage backend is local, that file has to be pulled locally. Test that
        the proper calls are made.
        '''

        base_dir = '/foo'
        mock_settings.DATA_DIR = base_dir

        resources = Resource.objects.filter(owner=self.regular_user_1)
        r = resources[0]
        original_path = r.path
        filename = r.name
        owner_uuid = self.regular_user_1.pk
        expected_basename = '{uuid}.{name}'.format(
            uuid = str(r.pk),
            name = filename
        )
        expected_destination = os.path.join(base_dir, \
            DUMMY_DIRNAME,
            Resource.USER_RESOURCE_STORAGE_DIRNAME, \
            str(owner_uuid), expected_basename)

        # using False here makes it seem like the Resource is not local
        # and that the 
        mock_os_exists.side_effect = [True, False]

        mock_localize_remote_resource.return_value = expected_destination
        storage_backend = LocalStorage()
        path = storage_backend.store(r)

        self.assertEqual(path, expected_destination)
        mock_localize_remote_resource.assert_called()
        mock_make_local_dir.assert_not_called()
        