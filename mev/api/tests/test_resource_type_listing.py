import unittest
import unittest.mock as mock

from django.urls import reverse
from rest_framework import status

from constants import DATABASE_RESOURCE_TYPES
from resource_types import RESOURCE_MAPPING
from api.tests.base import BaseAPITestCase


class TestResourceTypeList(BaseAPITestCase):

    def setUp(self):
        self.url = reverse('resource-type-list')
        self.establish_clients()

    def test_description_attribute_filled(self):
        '''
        To properly provide the list of all available
        resource types, need to ensure that the DESCRIPTION
        field is filled on all the "registered" types
        (not necessarily the abstract types)
        '''
        for key, title in DATABASE_RESOURCE_TYPES:
            resource_type_class = RESOURCE_MAPPING[key]
            # if the DESCRIPTION attribute was forgotten,
            # the following will raise an exception:
            description =  resource_type_class.DESCRIPTION

    def test_response_payload(self):
        response = self.authenticated_regular_client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)