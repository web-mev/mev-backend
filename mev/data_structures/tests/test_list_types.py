import unittest

from data_structures.list_attributes import StringListAttribute, \
    UnrestrictedStringListAttribute, \
    BoundedFloatListAttribute

from exceptions import DataStructureValidationException, \
    AttributeValueError, \
    MissingAttributeKeywordError

from helpers import normalize_identifier


class TestStringListAttributes(unittest.TestCase):

    def test_creation(self):
        mylist = ['a','b','c']
        s = StringListAttribute(mylist)
        dict_rep = s.to_dict()
        expected = {
            'attribute_type': 'StringList',
            'value': mylist
        }
        self.assertDictEqual(dict_rep, expected)

        mylist = ['a b','c']
        modified_list = [normalize_identifier(x) for x in mylist]
        s = StringListAttribute(mylist)
        dict_rep = s.to_dict()
        expected = {
            'attribute_type': 'StringList',
            'value': modified_list
        }
        self.assertDictEqual(dict_rep, expected)

        s = UnrestrictedStringListAttribute(mylist)
        dict_rep = s.to_dict()
        expected = {
            'attribute_type': 'UnrestrictedStringList',
            'value': mylist
        }
        self.assertDictEqual(dict_rep, expected)

    def test_creation_fail(self):        

        # the second entry is invalid:
        mylist = ['a','?b','c']
        with self.assertRaises(AttributeValueError):
            s = StringListAttribute(mylist)

        # test that we need a list
        with self.assertRaisesRegex(DataStructureValidationException, 'list'):
            raise StringListAttribute('a')


class TestBoundedFloatListAttributes(unittest.TestCase):

    def test_creation(self):
        mylist = [0.05, 0.1]
        b = BoundedFloatListAttribute([0.05,0.1],
            min=0.0, max=1.0)
        dict_rep = b.to_dict()
        expected = {
            'attribute_type': 'BoundedFloatList',
            'value': mylist
        }
        self.assertDictEqual(dict_rep, expected)

    def test_creation_fails(self):

        # a missing keyword
        with self.assertRaisesRegex(MissingAttributeKeywordError, 'min'):
            b = BoundedFloatListAttribute([0.03,0.05], max=1.0)

        # an invalid value:
        with self.assertRaisesRegex(
            AttributeValueError, 'not within the bounds'):
            b = BoundedFloatListAttribute(
                [0.1, 1.1, 0.4],  # <-- value exceeds the max
                min = 0.0,
                max = 1.0
            )