import unittest

from rest_framework.serializers import ValidationError

from api.data_structures import IntegerAttribute, \
    PositiveIntegerAttribute, \
    NonnegativeIntegerAttribute, \
    FloatAttribute, \
    StringAttribute

class TestAttributes(unittest.TestCase):

    def test_attribute_equality(self):
        a1 = FloatAttribute(2.3)
        a2 = FloatAttribute(2.3)
        self.assertTrue(a1 == a2)


    def test_integer_attribute(self):
        i = IntegerAttribute(44)
        self.assertEqual(i.value, 44)
        i = IntegerAttribute(-3)
        self.assertEqual(i.value, -3)


    def test_float_rejected_for_integer(self):
        with self.assertRaises(ValidationError):
            IntegerAttribute(1.2)


    def test_int_string_rejected_for_integer(self):
        with self.assertRaises(ValidationError):
            IntegerAttribute('2')


    def test_positive_integer_attribute(self):
        i = PositiveIntegerAttribute(44)
        self.assertEqual(i.value, 44)

        with self.assertRaises(ValidationError):
            PositiveIntegerAttribute(-3)

        with self.assertRaises(ValidationError):
            PositiveIntegerAttribute(0)


    def test_nonnegative_integer_attribute(self):
        i = NonnegativeIntegerAttribute(44)
        self.assertEqual(i.value, 44)

        i = NonnegativeIntegerAttribute(0)
        self.assertEqual(i.value, 0)

        with self.assertRaises(ValidationError):
            NonnegativeIntegerAttribute(-3)


    def test_float_attribute(self):
        f = FloatAttribute(3.4)
        self.assertEqual(f.value, 3.4)

        # accepts integers and converts to float
        f = FloatAttribute(3)
        self.assertEqual(f.value, 3.0)

        f = FloatAttribute(-3.1)
        self.assertEqual(f.value, -3.1)

        # can't specify a float as a string
        with self.assertRaises(ValidationError):
            FloatAttribute('3.4')


    def test_string_attribute(self):
        # this is sort of double test-coverage, but that can't hurt
        s = StringAttribute('abc')
        self.assertEqual(s.value, 'abc')

        with self.assertRaises(ValidationError):
            StringAttribute('-9abc')

        with self.assertRaises(ValidationError):
            StringAttribute(3.4)