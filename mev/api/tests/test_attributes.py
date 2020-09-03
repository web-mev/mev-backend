import unittest
import uuid
import random

from rest_framework.serializers import ValidationError

from api.data_structures import IntegerAttribute, \
    PositiveIntegerAttribute, \
    NonnegativeIntegerAttribute, \
    FloatAttribute, \
    PositiveFloatAttribute, \
    NonnegativeFloatAttribute, \
    StringAttribute, \
    BoundedIntegerAttribute, \
    BoundedFloatAttribute, \
    BooleanAttribute, \
    DataResourceAttribute


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

    def test_positive_float_attribute(self):
        f = PositiveFloatAttribute(4.4)
        self.assertEqual(f.value, 4.4)

        with self.assertRaises(ValidationError):
            PositiveFloatAttribute(-3.2)

        with self.assertRaises(ValidationError):
            PositiveFloatAttribute(0)

    def test_nonnegative_float_attribute(self):
        f = NonnegativeFloatAttribute(4.4)
        self.assertEqual(f.value, 4.4)

        f = NonnegativeFloatAttribute(0.0)
        self.assertEqual(f.value, 0.0)

        with self.assertRaises(ValidationError):
            NonnegativeFloatAttribute(-3.2)

    def test_string_attribute(self):
        # this is sort of double test-coverage, but that can't hurt
        s = StringAttribute('abc')
        self.assertEqual(s.value, 'abc')

        with self.assertRaises(ValidationError):
            StringAttribute('-9abc')

        with self.assertRaises(ValidationError):
            StringAttribute(3.4)

    def test_missing_keys_for_bounded_attributes(self):

        for clazz in [BoundedIntegerAttribute, BoundedFloatAttribute]:
            # test missing min key
            with self.assertRaises(ValidationError):
                i = clazz(3, max=10)
        
            # test missing max key
            with self.assertRaises(ValidationError):
                i = clazz(3, min=0)

            # test missing both keys
            with self.assertRaises(ValidationError):
                i = clazz(3)

    def test_bounded_integer_atttribute(self):

        # test a valid bounded int
        i = BoundedIntegerAttribute(3, min=0, max=5)
        self.assertEqual(i.value, 3)

        # within bounds, but a float
        with self.assertRaises(ValidationError):
            i = BoundedIntegerAttribute(3.3, min=0, max=5)

        # out of bounds (over)
        with self.assertRaises(ValidationError):
            i = BoundedIntegerAttribute(12, min=0, max=10)

        # out of bounds (under)
        with self.assertRaises(ValidationError):
            i = BoundedIntegerAttribute(-2, min=0, max=10)

        # out of bounds (under) AND wrong type
        with self.assertRaises(ValidationError):
            i = BoundedIntegerAttribute(-2.2, min=0, max=10)

        # bounds are wrong type.  Since we want an integer,
        # the bounds should be integers also.
        with self.assertRaises(ValidationError):
            i = BoundedIntegerAttribute(2, min=0.1, max=10)
        with self.assertRaises(ValidationError):
            i = BoundedIntegerAttribute(2, min=0, max=10.2)
        with self.assertRaises(ValidationError):
            i = BoundedIntegerAttribute(2, min=0.1, max=10.2)

        # out of bounds AND wrong type of bounds
        with self.assertRaises(ValidationError):
            i = BoundedIntegerAttribute(22, min=0.1, max=10.2)

    def test_bounded_float_atttribute(self):

        # test a valid bounded float
        f = BoundedFloatAttribute(0.2, min=0, max=1.0)
        self.assertEqual(f.value, 0.2)

        # within bounds, but int
        f = BoundedFloatAttribute(3.3, min=0, max=5)
        self.assertEqual(f.value, 3.3)

        # within bounds, equal to max
        f = BoundedFloatAttribute(5.0, min=0, max=5)
        self.assertEqual(f.value, 5.0)

        # out of bounds (over)
        with self.assertRaises(ValidationError):
            f = BoundedFloatAttribute(1.2, min=0, max=1.0)

        # out of bounds (under)
        with self.assertRaises(ValidationError):
            f = BoundedFloatAttribute(-2.2, min=0, max=10)

        # you CAN specify integer bounds for bounded floats
        f = BoundedFloatAttribute(2.2, min=0, max=10)
        f = BoundedFloatAttribute(2.2, min=0.2, max=10.5)

    def test_boolean_attribute(self):
        '''
        Tests that a range of canonical values can be used to specify
        whether a boolean attribute is true or false.
        '''
        b = BooleanAttribute('true')
        self.assertTrue(b.value)
        b = BooleanAttribute('True')
        self.assertTrue(b.value)
        b = BooleanAttribute(1)
        self.assertTrue(b.value)
        b = BooleanAttribute(True)
        self.assertTrue(b.value)
        with self.assertRaises(ValidationError):
            b = BooleanAttribute(2)

        b = BooleanAttribute('false')
        self.assertFalse(b.value)
        b = BooleanAttribute('False')
        self.assertFalse(b.value)
        b = BooleanAttribute(0)
        self.assertFalse(b.value)
        b = BooleanAttribute(False)
        self.assertFalse(b.value)
        with self.assertRaises(ValidationError):
            b = BooleanAttribute(-1)

    def test_dataresource_attribute(self):
        '''
        Tests the DataResourceAttribute, which is used when specifying files
        for use in analysis `Operation`s.
        '''

        # works:
        d = DataResourceAttribute(str(uuid.uuid4()), many=True)
        d = DataResourceAttribute(str(uuid.uuid4()), many=False)

        # should fail since multiple UUID passed, but many=False
        with self.assertRaises(ValidationError):
            DataResourceAttribute(
                [str(uuid.uuid4()), str(uuid.uuid4())], 
                many=False
            )

        # should fail since one of the vals is NOT a UUID
        with self.assertRaises(ValidationError):
            DataResourceAttribute(
                [str(uuid.uuid4()), 'abc'], 
                many=True
            )

        # the "value" is not a UUID. Should fail:
        with self.assertRaises(ValidationError):
            DataResourceAttribute('abc')