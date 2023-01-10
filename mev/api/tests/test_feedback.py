import unittest.mock as mock

from django.urls import reverse
from rest_framework import status

from api.models import FeedbackMessage
from api.tests.base import BaseAPITestCase
from api.tests import test_settings

class FeedbackTests(BaseAPITestCase):

    def setUp(self):
        self.url = reverse('feedback')
        self.establish_clients()

    def test_admin_can_list_messages(self):
        """
        Only admins should be able to view the messages (e.g. 
        as part of a dashboard)
        """
        response = self.authenticated_admin_client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        j = response.json()
        self.assertTrue(len(j) == 1)
        x = j[0]
        self.assertTrue('message' in x)
        self.assertTrue('timestamp' in x)
        self.assertTrue('user_email' in x)


    def test_regular_users_not_permitted(self):
        response = self.authenticated_regular_client.get(self.url)
        self.assertTrue(response.status_code == status.HTTP_403_FORBIDDEN)

    def test_submit_message_blocked_if_not_authenticated(self):
        payload = {
            'message': 'Here is a feedback message'
        }
        response = self.regular_client.post(self.url, data=payload, format='json')
        self.assertTrue(response.status_code == status.HTTP_401_UNAUTHORIZED)

    @mock.patch('api.views.feedback_views.send_email_to_admins')
    def test_submit_message(self, mock_send_email_to_admins):
        orig_messages = FeedbackMessage.objects.all()
        n0 = len(orig_messages)
        msg = 'Here is a feedback message'
        msg_to_admin = msg + '\nFrom: reguser1@foo.com'
        payload = {
            'message': msg
        }
        response = self.authenticated_regular_client.post(self.url, data=payload, format='json')
        self.assertTrue(response.status_code == status.HTTP_201_CREATED)
        j = response.json()
        self.assertTrue('user_email' in j)
        # check that we added a message to the db
        final_messages = FeedbackMessage.objects.all()
        n1 = len(final_messages)
        self.assertEqual(n1 - n0, 1)
        mock_send_email_to_admins.assert_called_with(msg_to_admin)

    def test_malformatted_message(self):
        orig_messages = FeedbackMessage.objects.all()
        n0 = len(orig_messages)
        payload = {'bad_key': '!!!'}
        response = self.authenticated_regular_client.post(self.url, data=payload, format='json')
        j = response.json()
        self.assertTrue('message' in j)
        self.assertTrue(response.status_code == status.HTTP_400_BAD_REQUEST)
        final_messages = FeedbackMessage.objects.all()
        n1 = len(final_messages)
        self.assertEqual(n1 - n0, 0)