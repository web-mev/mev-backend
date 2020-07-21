import unittest
import unittest.mock as mock

from resource_types import DATABASE_RESOURCE_TYPES, RESOURCE_MAPPING


class TestResourceTypeList(unittest.TestCase):

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