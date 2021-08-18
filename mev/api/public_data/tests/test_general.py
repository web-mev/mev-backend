import unittest
import unittest.mock as mock

from django.conf import settings

from api.public_data import DATASETS


class TestPublicDatasets(unittest.TestCase): 

    def test_unique_tags(self):
        '''
        This test serves as a check that we did not accidentally duplicate
        a tag (the `TAG` attribute on the implementing public dataset classes)
        '''
        unique_tags = set(DATASETS)
        self.assertTrue(len(unique_tags) == len(DATASETS))

