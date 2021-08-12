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

class PublicDataCreateTests(BaseAPITestCase):
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
        self.url = reverse('public-dataset-create', 
            kwargs={'dataset_id': self.test_active_dataset.index_name}
        )
        self.establish_clients()

    @mock.patch('api.views.public_dataset.prepare_dataset')
    @mock.patch('api.views.public_dataset.check_if_valid_public_dataset_name')
    def test_admin_only(self, 
        mock_check_if_valid_public_dataset_name,
        mock_prepare_dataset):
        """
        Test that only admins can perform this action
        """
        mock_check_if_valid_public_dataset_name.return_value = True

        # Both unauthenticated and authenticated regular clients should fail.
        response = self.regular_client.get(self.url)
        self.assertTrue((response.status_code == status.HTTP_401_UNAUTHORIZED) 
        | (response.status_code == status.HTTP_403_FORBIDDEN))

        response = self.authenticated_regular_client.get(self.url)
        self.assertTrue((response.status_code == status.HTTP_401_UNAUTHORIZED) 
        | (response.status_code == status.HTTP_403_FORBIDDEN))

        # try as an admin. Should return 200
        response = self.authenticated_admin_client.get(self.url)
        self.assertTrue(response.status_code == status.HTTP_200_OK)

    @mock.patch('api.views.public_dataset.prepare_dataset')
    @mock.patch('api.views.public_dataset.check_if_valid_public_dataset_name')
    def test_process_starts_for_existing_dataset(self, 
        mock_check_if_valid_public_dataset_name,
        mock_prepare_dataset):
        """
        Test that the data prep process is started and that the dataset
        is set to inactive. Here, the dataset was previously existing and
        in the database
        """
        mock_check_if_valid_public_dataset_name.return_value = True
        response = self.authenticated_admin_client.get(self.url)
        self.assertTrue(response.status_code == status.HTTP_200_OK)

        # calling the url will start the process of ingesting/prepping the data.
        # it should be made inactive
        index_name = self.test_active_dataset.index_name
        db_record = PublicDataset.objects.get(index_name = index_name)
        self.assertFalse(db_record.active)
        mock_prepare_dataset.delay.assert_called_with(self.test_active_dataset.pk)
        # check that no new records were added:
        current_datasets = PublicDataset.objects.all()
        self.assertTrue(len(self.all_public_datasets) == len(current_datasets))

    @mock.patch('api.views.public_dataset.prepare_dataset')
    @mock.patch('api.views.public_dataset.check_if_valid_public_dataset_name')
    def test_process_starts_for_new_dataset(self, 
        mock_check_if_valid_public_dataset_name,
        mock_prepare_dataset):
        """
        Test that the data prep process is started and that the dataset
        is set to inactive. Here, the dataset is new. It does, however,
        have to be "known about". That is, we obviously cannot have a 
        dataset indexed if we don't know the schema etc. We pretend
        that we know of this dataset here by mocking.
        """
        mock_check_if_valid_public_dataset_name.return_value = True
        mock_index_name = 'foo-abc'
        # double-check to make sure there's no record in the test DB
        # for this mock index
        matching_index = PublicDataset.objects.filter(index_name = mock_index_name)
        self.assertTrue(len(matching_index) == 0)

        url = reverse('public-dataset-create', 
            kwargs={'dataset_id': mock_index_name}
        )
        response = self.authenticated_admin_client.get(url)
        self.assertTrue(response.status_code == status.HTTP_200_OK)

        # calling the url will start the process of ingesting/prepping the data.
        # it should be made inactive
        db_record = PublicDataset.objects.get(index_name = mock_index_name)
        self.assertFalse(db_record.active)
        mock_prepare_dataset.delay.assert_called_with(db_record.pk)

        # Check there is a new record (kind of a double check )
        current_datasets = PublicDataset.objects.all()
        self.assertTrue(
            (len(current_datasets)- len(self.all_public_datasets)) == 1
        )

    @mock.patch('api.views.public_dataset.prepare_dataset')
    @mock.patch('api.views.public_dataset.check_if_valid_public_dataset_name')
    def test_attempt_to_add_unknown_dataset_fails(self, 
        mock_check_if_valid_public_dataset_name,
        mock_prepare_dataset):
        """
        Test that "unknown" datasets are rejected. This would be the case if someone
        tries to index a dataset that we haven't seen before. More likely, this would 
        be caught in cases where there is a typo for the intended "known" dataset
        """
        mock_check_if_valid_public_dataset_name.return_value = False
        mock_index_name = 'foo-abc'
        # double-check to make sure there's no record in the test DB
        # for this mock index
        matching_index = PublicDataset.objects.filter(index_name = mock_index_name)
        self.assertTrue(len(matching_index) == 0)

        url = reverse('public-dataset-create', 
            kwargs={'dataset_id': mock_index_name}
        )
        response = self.authenticated_admin_client.get(url)
        self.assertTrue(response.status_code == status.HTTP_400_BAD_REQUEST)
        mock_prepare_dataset.delay.assert_not_called()

        # check that no new records were added:
        current_datasets = PublicDataset.objects.all()
        self.assertTrue(len(self.all_public_datasets) == len(current_datasets))
