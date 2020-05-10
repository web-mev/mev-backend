import unittest

from rest_framework.serializers import ValidationError

from api.data_structures import IntegerAttribute, \
    PositiveIntegerAttribute, \
    NonnegativeIntegerAttribute, \
    FloatAttribute, \
    StringAttribute, \
    all_attribute_types
from api.exceptions import StringIdentifierException

class TestAttributes(unittest.TestCase):

    def test_bad_key_raises_exception(self):
        bad_key = '9a' # bad since starts with a non-letter
        for T in all_attribute_types:
            with self.assertRaises(StringIdentifierException):
                # the "value" (2nd arg) does not matter since the name
                # should be rejected first.
                T(bad_key, 0)

    def test_integer_attribute(self):
        i = IntegerAttribute('somekey', 44)
        self.assertEqual(i.value, 44)
        i = IntegerAttribute('somekey', -3)
        self.assertEqual(i.value, -3)


    def test_float_rejected_for_integer(self):
        with self.assertRaises(ValidationError):
            IntegerAttribute('somekey', 1.2)

    def test_int_string_rejected_for_integer(self):
        with self.assertRaises(ValidationError):
            IntegerAttribute('somekey', '2')

    def test_positive_integer_attribute(self):
        i = PositiveIntegerAttribute('somekey', 44)
        self.assertEqual(i.value, 44)

        with self.assertRaises(ValidationError):
            PositiveIntegerAttribute('somekey', -3)

        with self.assertRaises(ValidationError):
            PositiveIntegerAttribute('somekey', 0)

    def test_nonnegative_integer_attribute(self):
        i = NonnegativeIntegerAttribute('somekey', 44)
        self.assertEqual(i.value, 44)

        i = NonnegativeIntegerAttribute('somekey', 0)
        self.assertEqual(i.value, 0)

        with self.assertRaises(ValidationError):
            NonnegativeIntegerAttribute('somekey', -3)

    def test_float_attribute(self):
        f = FloatAttribute('somekey', 3.4)
        self.assertEqual(f.value, 3.4)

        # accepts integers and converts to float
        f = FloatAttribute('somekey', 3)
        self.assertEqual(f.value, 3.0)

        f = FloatAttribute('somekey', -3.1)
        self.assertEqual(f.value, -3.1)

        with self.assertRaises(ValidationError):
            FloatAttribute('somekey', '3.4')
