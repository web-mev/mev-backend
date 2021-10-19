import unittest.mock as mock
from urllib.parse import quote as param_encoder
from django.urls import reverse
from django.core.exceptions import ImproperlyConfigured
from rest_framework import status

from api.models import PublicDataset
from api.tests.base import BaseAPITestCase
from api.tests import test_settings


class PublicDataListTests(BaseAPITestCase):
    def setUp(self):
        self.url = reverse('public-dataset-list')
        self.establish_clients()
        self.all_public_datasets = PublicDataset.objects.all()
        if len(self.all_public_datasets) == 0:
            raise ImproperlyConfigured('Need at least one active public dataset to'
                ' run this test properly.'
            )
        self.all_active_datasets = [x for x in self.all_public_datasets if x.active]
        if len(self.all_active_datasets) == 0:
            raise ImproperlyConfigured('Need at least one active public dataset to'
                ' run this test properly.'
            )

    def test_list_requires_auth(self):
        """
        Test that general requests to the endpoint generate 401
        """
        response = self.regular_client.get(self.url)
        self.assertTrue((response.status_code == status.HTTP_401_UNAUTHORIZED) 
        | (response.status_code == status.HTTP_403_FORBIDDEN))

        response = self.authenticated_regular_client.get(self.url)
        self.assertTrue((response.status_code == status.HTTP_200_OK))
        self.assertTrue(len(response.json()) == len(self.all_active_datasets))


class PublicDataQueryTests(BaseAPITestCase):
    '''
    Tests focused around the ability to add/create public datasets.
    '''
    def setUp(self):
        self.all_public_datasets = PublicDataset.objects.all()
        if len(self.all_public_datasets) == 0:
            raise ImproperlyConfigured('Need at least one active public dataset to'
                ' run this test properly.'
            )
        self.all_active_datasets = [x for x in self.all_public_datasets if x.active]
        if len(self.all_active_datasets) == 0:
            raise ImproperlyConfigured('Need at least one active public dataset to'
                ' run this test properly.'
            )
        # grab the first active dataset to use in the tests below
        self.test_active_dataset = self.all_active_datasets[0]
        self.url = reverse('public-dataset-query', 
            kwargs={'dataset_id': self.test_active_dataset.index_name}
        )
        self.establish_clients()

    @mock.patch('api.views.public_dataset.query_dataset')
    def test_call_format(self, mock_query_dataset):
        '''
        Test that the proper request is made 
        '''
        query_str = 'q=*:*&facet.field=foo&facet=on'
        encoded_str = 'q=%2A%3A%2A&facet.field=foo&facet=on'
        url = self.url + '?' + query_str
        mock_response_json = {'a':1, 'b':2}
        mock_query_dataset.return_value = mock_response_json
        response = self.authenticated_admin_client.get(url)
        mock_query_dataset.assert_called_with(self.test_active_dataset.index_name, encoded_str)