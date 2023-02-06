from django.urls import reverse
from django.test import override_settings

from api.tests.base import BaseAPITestCase


class GlobusUploadTests(BaseAPITestCase):

    def setUp(self):
        self.globus_init_url = reverse('globus-init')
        self.globus_upload_url = reverse('globus-upload')
        self.establish_clients()

    @override_settings(GLOBUS_ENABLED=False)
    def test_disabled_globus_returns_400(self):
        r = self.authenticated_regular_client.get(self.globus_init_url)
        self.assertEqual(r.status_code, 400)


    @override_settings(GLOBUS_ENABLED=True)
    def test_enabled_globus_returns_200(self):
        r = self.authenticated_regular_client.get(self.globus_init_url)
        self.assertEqual(r.status_code, 200)