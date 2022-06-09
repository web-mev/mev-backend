import unittest
import unittest.mock as mock

from constants import ANNOTATION_TABLE_KEY

from django.urls import reverse
from django.core.exceptions import ImproperlyConfigured
from rest_framework import status

from constants import DATABASE_RESOURCE_TYPES
from resource_types import RESOURCE_MAPPING, AnnotationTable
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
        j = response.json()

        # for one of the resource types, check that the payload includes
        # the (nested) info about the formats we accept.
        target_key = ANNOTATION_TABLE_KEY
        found = False
        i = 0
        N = len(j)
        d = None
        while (not found) and (i < N):
            x = j[i]
            if x['resource_type_key'] == target_key:
                d = x
                found = True
            i += 1
        if d is None:
            raise ImproperlyConfigured('The expected part of the payload was not found')

        acceptable_format_keys = [x['key'] for x in d['acceptable_formats']]
        expected_formats = AnnotationTable.ACCEPTABLE_FORMATS
        self.assertCountEqual(acceptable_format_keys, expected_formats)