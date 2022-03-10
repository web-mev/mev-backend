import unittest
import unittest.mock as mock

from django.core.exceptions import ImproperlyConfigured

from api.tests.base import BaseAPITestCase
from api.container_registries import get_container_registry, \
    infer_container_registry_based_on_prefix
from api.container_registries.github_cr import GithubContainerRegistry
from api.container_registries.dockerhub_cr import DockerhubRegistry


class DockerRegistryTester(BaseAPITestCase):

    @mock.patch('api.container_registries.settings')
    def test_invalid_container_registry_raises_ex(self, mock_settings):
        mock_settings.CONTAINER_REGISTRY = 'SOMETHING_BAD'

        with self.assertRaisesRegex(Exception, 'Invalid'):
            get_container_registry()

    @mock.patch('api.container_registries.settings')
    def test_valid_container_registries(self, mock_settings):
        mock_settings.CONTAINER_REGISTRY = 'github'
        reg = get_container_registry()
        self.assertTrue(type(reg) is GithubContainerRegistry)

        mock_settings.CONTAINER_REGISTRY = 'dockerhub'
        reg = get_container_registry()
        self.assertTrue(type(reg) is DockerhubRegistry)

    def test_container_registry_inference(self):
        '''
        Test that the returned registry is correct based on the 
        registry prefix
        '''
        reg = infer_container_registry_based_on_prefix('ghcr.io')
        self.assertTrue(type(reg) is GithubContainerRegistry)

        reg = infer_container_registry_based_on_prefix('docker.io')
        self.assertTrue(type(reg) is DockerhubRegistry)

        with self.assertRaisesRegex(Exception, 'did not correspond'):
            infer_container_registry_based_on_prefix('foo.io')
