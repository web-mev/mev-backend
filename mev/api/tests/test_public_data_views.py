from io import BytesIO
import unittest.mock as mock

from urllib.parse import quote as param_encoder
from django.urls import reverse
from django.core.files import File
from django.core.exceptions import ImproperlyConfigured
from rest_framework import status

from api.models import PublicDataset, Workspace, Resource
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


class PublicDataDetailsTests(BaseAPITestCase):
    '''
    Tests focused around the ability to query a specific public dataset.
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
        self.url = reverse('public-dataset-details', 
            kwargs={'dataset_id': self.test_active_dataset.index_name}
        )
        self.establish_clients()

    def test_requires_auth(self):
        """
        Test that general requests to the endpoint generate 401
        """
        response = self.regular_client.get(self.url)
        self.assertTrue((response.status_code == status.HTTP_401_UNAUTHORIZED) 
        | (response.status_code == status.HTTP_403_FORBIDDEN))

        response = self.authenticated_regular_client.get(self.url)
        self.assertTrue((response.status_code == status.HTTP_200_OK))

    def test_returns_expected_details(self):
        response = self.authenticated_regular_client.get(self.url)
        self.assertTrue((response.status_code == status.HTTP_200_OK))
        response_json = response.json()
        self.assertTrue(response_json['index_name'] == self.test_active_dataset.index_name)
        print(response_json)

    def test_inactive_instance_returns_404(self):
        '''
        If the details are requested on an inactive dataset, return a 404
        '''
        # check that we have an inactive dataset first:
        dataset_tag = 'public-baz'
        pd = PublicDataset.objects.get(index_name = dataset_tag)
        self.assertFalse(pd.active)
        url = reverse('public-dataset-details', 
            kwargs={'dataset_id': dataset_tag}
        )
        response = self.authenticated_regular_client.get(url)
        self.assertTrue((response.status_code == status.HTTP_404_NOT_FOUND))


class PublicDataQueryTests(BaseAPITestCase):
    '''
    Tests focused around the ability to query public datasets.
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


class PublicDataCreateTests(BaseAPITestCase):
    '''
    Tests focused around the ability to create public datasets.
    '''
    def setUp(self):

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
        # grab the first active dataset to use in the tests below
        self.test_active_dataset = self.all_active_datasets[0]
        self.url = reverse('public-dataset-create', 
            kwargs={'dataset_id': self.test_active_dataset.index_name}
        )

    def test_requires_auth(self):
        """
        Test that general requests to the endpoint generate 401
        """
        response = self.regular_client.post(self.url)
        self.assertTrue((response.status_code == status.HTTP_401_UNAUTHORIZED) 
        | (response.status_code == status.HTTP_403_FORBIDDEN))

    @mock.patch('api.views.public_dataset.async_create_dataset_from_params')
    def test_error_reported(self, mock_async_create_dataset_from_params):
        '''
        If something goes wrong in the call to the async
        public data function, we return a 400 and report it.
        '''
        # this is the payload we want passed to the function.
        # the full request will have this AND the workspace
        payload = {'samples': [1,2,3]}

        # mock the failure:
        mock_async_create_dataset_from_params.delay.side_effect = Exception('something bad!')

        response = self.authenticated_regular_client.post(
            self.url, data=payload, format='json')
        self.assertTrue(response.status_code == status.HTTP_400_BAD_REQUEST)

    @mock.patch('api.views.public_dataset.async_create_dataset_from_params')
    def test_async_call(self, mock_async_create_dataset_from_params):
        '''
        Test that we call the async function with the proper args
        '''
        payload = {}

        response = self.authenticated_regular_client.post(
            self.url, data=payload, format='json')
        self.assertTrue(response.status_code == status.HTTP_204_NO_CONTENT)

        mock_async_create_dataset_from_params.delay.assert_called_with(
            self.test_active_dataset.index_name,
            self.regular_user_1.pk,
            None, 
            ''
        )
        self.assertTrue(response.status_code == status.HTTP_204_NO_CONTENT)

        # now test with actual filtering params
        mock_async_create_dataset_from_params.reset_mock()

        payload = {'filters': {'a':1}}

        # finally, call the endpoint
        response = self.authenticated_regular_client.post(
            self.url, data=payload, format='json')
        self.assertTrue(response.status_code == status.HTTP_204_NO_CONTENT)

        # below, we check that the workspace key gets stripped
        # from the call to the creation method
        mock_async_create_dataset_from_params.delay.assert_called_with(
            self.test_active_dataset.index_name,
            self.regular_user_1.pk,
            payload['filters'],
            ''
        )

        mock_async_create_dataset_from_params.delay.reset_mock()
        output_name = 'foo'
        payload = {'filters': {'a':1}, 'output_name': output_name}

        # finally, call the endpoint
        response = self.authenticated_regular_client.post(
            self.url, data=payload, format='json')
        self.assertTrue(response.status_code == status.HTTP_204_NO_CONTENT)

        # below, we check that the workspace key gets stripped
        # from the call to the creation method
        mock_async_create_dataset_from_params.delay.assert_called_with(
            self.test_active_dataset.index_name,
            self.regular_user_1.pk,
            payload['filters'],
            output_name
        )

    @mock.patch('api.views.public_dataset.async_create_dataset_from_params')
    def test_rejects_malformatted_filter(self, mock_async_create_dataset_from_params):
        '''
        Test that if a 'filter' key is provided and it is not parsed 
        as a dict, then we reject
        '''
        payload = {
            'filters': 'abc'
        }
        response = self.authenticated_regular_client.post(
            self.url, data=payload, format='json')
        self.assertTrue(response.status_code == status.HTTP_400_BAD_REQUEST)
        mock_async_create_dataset_from_params.delay.assert_not_called()
