import unittest

from rest_framework.serializers import ValidationError

from api.data_structures import StringListAttribute, UnrestrictedStringListAttribute

class TestListAttributes(unittest.TestCase):

    def test_string_attribute(self):
        v = ['abc', 'def', 'xyz']
        s = StringListAttribute(v)

        v = ['abc', '??']
        with self.assertRaises(ValidationError):
            s = StringListAttribute(v)


    def test_unrestricted_string_attribute(self):
        v = ['abc', 'def', 'xyz']
        s = UnrestrictedStringListAttribute(v)

        v = ['abc', '??']
        s = UnrestrictedStringListAttribute(v)
