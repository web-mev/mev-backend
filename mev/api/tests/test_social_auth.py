import unittest
import unittest.mock as mock

from django.conf import settings
from django.urls import reverse
import social_core
from rest_framework.exceptions import ValidationError
from rest_framework import status

from api.tests.base import BaseAPITestCase
from api.views.social_views import do_auth

class TestSocialAuth(unittest.TestCase):
    '''
    This suite of tests checks parts of the authentication process that 
    are not related to the request/response handling.
    '''

    def test_general_failure_tries_multiple_times(self):
        '''
        When we call the `do_auth` function (part of social_core
        package), if the request fails for some general reason
        (e.g. network hiccup), we test that it tries again
        '''
        mock_backend = mock.MagicMock()
        mock_request = mock.MagicMock()
        mock_backend.do_auth.side_effect = Exception('something bad!')
        mock_request.backend = mock_backend
        result = do_auth(mock_request, 'abc')
        self.assertIsNone(result)
        self.assertEqual(settings.MAX_RETRIES, mock_backend.do_auth.call_count)

    def test_immediate_auth_failure_does_not_retry(self):
        '''
        Bad tokens end up raising social_core.exceptions.AuthForbidden 
        exceptions.  If that's raised, we immediately exit our
        `do_auth` function.
        '''
        mock_backend = mock.MagicMock()
        mock_request = mock.MagicMock()
        mock_backend.do_auth.side_effect = social_core.exceptions.AuthForbidden('something bad!')
        mock_request.backend = mock_backend
        with self.assertRaises(ValidationError):
            do_auth(mock_request, 'abc')
        self.assertEqual(1, mock_backend.do_auth.call_count)


class GoogleOauth2RequestTests(BaseAPITestCase):

    def setUp(self):
        self.establish_clients()
        self.url = reverse('google-social')

    @mock.patch('api.views.social_views.register_by_access_token')
    def test_(self, mock_register_by_access_token):
        """
        Test that general requests to the endpoint generate 401
        """
        mock_register_by_access_token.return_value = self.regular_user_1

        payload = {'provider_token': 'abc123'}
        response = self.regular_client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue('access' in response.json())
        self.assertTrue('refresh' in response.json())