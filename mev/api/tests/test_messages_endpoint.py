from django.urls import reverse
from django.core.exceptions import ImproperlyConfigured
from rest_framework import status

from api.models import Message
from api.tests.base import BaseAPITestCase
from api.tests import test_settings


class MessageTests(BaseAPITestCase):
    '''
    Tests related to the 'messages' endpoint. This endpoint allows us
    to display ephemeral messages to users (such as updates, maintenance, etc.)
    '''
    def setUp(self):

        self.list_url = reverse('messages')
        self.latest_message_url = reverse('latest-message')
        self.create_url = reverse('message-add')
        self.establish_clients()

    def test_auth_not_required(self):
        """
        Test that we can use this url even if unauthenticated
        """
        response = self.regular_client.get(self.list_url)
        self.assertTrue(response.status_code == status.HTTP_200_OK)
        response = self.regular_client.get(self.latest_message_url)
        self.assertTrue(response.status_code == status.HTTP_200_OK) 

    def test_no_messages_returns_empty_list(self):
        '''
        If an admin has not added a message, simply return an
        empty list when querying the list interface
        '''
        response = self.regular_client.get(self.list_url)
        self.assertCountEqual([], response.json())

    def test_no_messages_returns_empty_object(self):
        '''
        If an admin has not added a message, simply return an
        empty object when querying the latest message endpiont
        '''
        response = self.regular_client.get(self.latest_message_url)
        self.assertCountEqual({}, response.json())

    def test_retrieves_all_messages(self):
        '''
        If multiple messages exist, we get them all
        '''
        m0 = Message.objects.create(message='This is msg0')
        m1 = Message.objects.create(message='This is msg1')
        
        response = self.regular_client.get(self.list_url)
        j = response.json()
        self.assertTrue(len(j) == 2)
        self.assertCountEqual(
            ['This is msg0','This is msg1'],
            [x['message'] for x in j]
        )

    def test_retrieves_latest_message(self):
        '''
        If multiple messages exist, we only get the
        most recent
        '''
        m0 = Message.objects.create(message='This is msg0')
        m1 = Message.objects.create(message='This is msg1')
        
        response = self.regular_client.get(self.latest_message_url)
        j = response.json()
        self.assertEqual(j['message'], 'This is msg1')

    def test_only_admin_can_create_message(self):
        '''
        Tests that unauthenticated and regular users are rejected from creating
        a message
        '''
        payload = {'message': 'some message'}
        response = self.regular_client.post(self.create_url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
                
        response = self.authenticated_regular_client.post(self.create_url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_message(self):
        '''
        Tests that adding a message (by an admin) works as expected
        '''
        payload = {'message': 'some message'}
        original_message = Message.objects.all()
        n0 = len(original_message)
        response = self.authenticated_admin_client.post(self.create_url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        final_messages = Message.objects.all().order_by('creation_datetime')
        n1 = len(final_messages)
        self.assertEqual(n1-n0, 1)
        m = final_messages[n1-1]
        self.assertEqual(m.message, 'some message')