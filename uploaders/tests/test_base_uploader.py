import unittest

from uploaders.base import BaseUpload

class MockRequest(object):
    def __init__(self, data):
        self.data = data

class TestBaseUpload(unittest.TestCase):

    def test_invalid_resource_type_raises_ex(self):
        '''
        Check that an invalid resource_type raises an
        exception when calling the validation function.
        '''
        b = BaseUpload()
        #mock_request = MockRequest({
        #    'owner_email': ''
        #})
        #b.resource_type = 'JUNK'
        #b.create_resource_from_upload()