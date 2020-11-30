import unittest

from rest_framework.serializers import ValidationError

from api.data_structures import StringListAttribute, UnrestrictedStringListAttribute

class TestListAttributes(unittest.TestCase):

    def test_string_attribute(self):
        v = ['abc', 'def', 'xyz']
        s = StringListAttribute(v)
        self.assertCountEqual(s.value, v)

        # test that setter works
        l = ['qqq', 'abc']
        s.value = l
        self.assertCountEqual(s.value, l)

        # test setting to None
        s.value = None
        self.assertIsNone(s.value)
        
        # check that the internal string values get 'converted'
        # (e.g. spaces replaced with underscores)
        v = ['a b c', 'd e']
        s = StringListAttribute(v)
        self.assertCountEqual(s.value, ['a_b_c','d_e'])

        # out of bounds values rejected
        v = ['abc', '??']
        with self.assertRaises(ValidationError):
            s = StringListAttribute(v)

        # test non-list items:
        v = 'abc'
        with self.assertRaises(ValidationError):
            StringListAttribute(v)



    def test_unrestricted_string_attribute(self):
        v = ['abc', 'def', 'xyz']
        s = UnrestrictedStringListAttribute(v)
        self.assertCountEqual(s.value, v)

        v = ['abc', '??']
        s = UnrestrictedStringListAttribute(v)
        self.assertCountEqual(s.value, v)
