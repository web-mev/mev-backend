import unittest.mock as mock
import os

from api.tests.base import BaseAPITestCase
from api.models import Resource
from api.storage_backends.local import LocalStorage

DUMMY_DIRNAME = 'userdir'

class TestLocalStorage(BaseAPITestCase):

    def setUp(self):
        self.establish_clients()

    @mock.patch('api.storage_backends.local.move_resource')
    @mock.patch('api.storage_backends.local.make_local_directory')
    @mock.patch('api.storage_backends.local.settings')
    @mock.patch('api.storage_backends.local.USER_STORAGE_DIRNAME', DUMMY_DIRNAME)
    def test_resource_path_altered_correctly(self, \
        mock_settings, \
        mock_make_local_dir, \
        mock_move):

        base_dir = '/foo'
        mock_settings.BASE_DIR = base_dir

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
            DUMMY_DIRNAME, str(owner_uuid), expected_basename)

        storage_backend = LocalStorage()
        storage_backend.store(r)

        self.assertEqual(r.path, expected_destination)

        