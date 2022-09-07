from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from django.conf import settings
from django.test import override_settings

from api.tests import test_settings

TEST_MEDIA_ROOT='/tmp/webmev_test/media_root'

@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class BaseAPITestCase(APITestCase):
    '''
    This defines the JSON-format "database" that can be loaded 
    to populate the database for testing.

    Classes deriving from this class will inherit this, so they have
    access to a mock database with the content.
    '''
    fixtures = [settings.TESTING_DB_DUMP]

    def establish_clients(self):
        '''
        This method creates suitable clients for testing the API calls.
        Called during the setUp methods in child classes.
        '''
        self.admin_user = get_user_model().objects.get(email=test_settings.ADMIN_USER.email)
        self.authenticated_admin_client = APIClient() 
        self.authenticated_admin_client.force_authenticate(user=self.admin_user)

        # get a "regular" user instance to use:
        self.regular_user_1 = get_user_model().objects.get(email=test_settings.REGULAR_USER_1.email)

        # client who is NOT authenticated
        self.regular_client = APIClient()

        # an authenticated "regular" client
        self.authenticated_regular_client = APIClient()
        self.authenticated_regular_client.force_authenticate(user=self.regular_user_1)

        # get another "regular" user instance to use and authenticate them:
        self.regular_user_2 = get_user_model().objects.get(email=test_settings.REGULAR_USER_2.email)
        self.authenticated_other_client = APIClient()
        self.authenticated_other_client.force_authenticate(user=self.regular_user_2)

import shutil
def tearDownModule():
    print("\nDeleting temporary files...\n"*200)
    try:
        shutil.rmtree(TEST_MEDIA_ROOT)
    except OSError:
        pass