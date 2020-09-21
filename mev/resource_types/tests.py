import unittest

from resource_types import RESOURCE_MAPPING

class TestResourceTypes(unittest.TestCase):    
    
    def test_all_resources_have_acceptable_extensions(self):
        '''
        If any of the resource types are missing the ACCEPTABLE_EXTENSIONS
        key, then this test will raise an AttributeError
        '''
        for k,v in RESOURCE_MAPPING.items():
            v.ACCEPTABLE_EXTENSIONS