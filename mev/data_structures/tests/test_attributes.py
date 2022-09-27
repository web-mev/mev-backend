import unittest
import uuid

from constants import POSITIVE_INF_MARKER, NEGATIVE_INF_MARKER

from data_structures.attribute_types import IntegerAttribute, \
    PositiveIntegerAttribute, \
    NonnegativeIntegerAttribute, \
    FloatAttribute, \
    PositiveFloatAttribute, \
    NonnegativeFloatAttribute, \
    StringAttribute, \
    UnrestrictedStringAttribute, \
    BoundedIntegerAttribute, \
    BoundedFloatAttribute, \
    BooleanAttribute, \
    DataResourceAttribute, \
    VariableDataResourceAttribute, \
    OperationDataResourceAttribute, \
    OptionStringAttribute

from exceptions import NullAttributeError, \
    AttributeValueError, \
    InvalidAttributeKeywordError, \
    MissingAttributeKeywordError


class TestSimpleAttributes(unittest.TestCase):
    '''
    Tests that the simple attribute types behave
    as expected.
    '''

    def test_attribute_equality(self):
        a1 = FloatAttribute(2.3)
        a2 = FloatAttribute(2.3)
        self.assertTrue(a1 == a2)

    def test_integer_attribute(self):
        i = IntegerAttribute(44)
        self.assertEqual(i.value, 44)

        # test the dict representation
        self.assertDictEqual(
            i.to_dict(),
            {
                'attribute_type': IntegerAttribute.typename,
                'value': 44
            }
        )

        i = IntegerAttribute(-3)
        self.assertEqual(i.value, -3)

        i = IntegerAttribute(None, allow_null=True)
        dict_rep = i.to_dict()
        expected_dict = {
            'attribute_type': 'Integer',
            'value': None
        }
        self.assertDictEqual(
            dict_rep,
            expected_dict
        )   

        with self.assertRaises(NullAttributeError):
            i = IntegerAttribute(None)

        with self.assertRaises(AttributeValueError):
            i = IntegerAttribute(POSITIVE_INF_MARKER)        

    def test_float_rejected_for_integer(self):
        with self.assertRaises(AttributeValueError):
            IntegerAttribute(1.2)

    def test_int_string_rejected_for_integer(self):
        with self.assertRaises(AttributeValueError):
            IntegerAttribute('2')

    def test_positive_integer_attribute(self):
        i = PositiveIntegerAttribute(44)
        self.assertEqual(i.value, 44)
        self.assertDictEqual(
            i.to_dict(),
            {
                'attribute_type': PositiveIntegerAttribute.typename,
                'value': 44
            }
        )

        with self.assertRaises(AttributeValueError):
            PositiveIntegerAttribute(-3)

        with self.assertRaises(AttributeValueError):
            PositiveIntegerAttribute(0)

        i = PositiveIntegerAttribute(None, allow_null=True)

        with self.assertRaises(NullAttributeError):
            PositiveIntegerAttribute(None)

    def test_nonnegative_integer_attribute(self):
        i = NonnegativeIntegerAttribute(44)
        self.assertEqual(i.value, 44)
        self.assertDictEqual(
            i.to_dict(),
            {
                'attribute_type': NonnegativeIntegerAttribute.typename,
                'value': 44
            }
        )
        i = NonnegativeIntegerAttribute(0)
        self.assertEqual(i.value, 0)

        with self.assertRaises(AttributeValueError):
            NonnegativeIntegerAttribute(-3)

        i = NonnegativeIntegerAttribute(None, allow_null=True)

        with self.assertRaises(NullAttributeError):
            NonnegativeIntegerAttribute(None)

    def test_float_attribute(self):
        f = FloatAttribute(3.4)
        self.assertEqual(f.value, 3.4)
        self.assertDictEqual(
            f.to_dict(),
            {
                'attribute_type': FloatAttribute.typename,
                'value': 3.4
            }
        )
        # accepts integers and converts to float
        f = FloatAttribute(3)
        self.assertEqual(f.value, 3.0)

        f = FloatAttribute(-3.1)
        self.assertEqual(f.value, -3.1)

        # can't specify a float as a string
        with self.assertRaises(AttributeValueError):
            FloatAttribute('3.4')

        # +/- infinity CAN be valid 
        f = FloatAttribute(POSITIVE_INF_MARKER)
        self.assertEqual(f.value, POSITIVE_INF_MARKER)
        f = FloatAttribute(NEGATIVE_INF_MARKER)
        self.assertEqual(f.value, NEGATIVE_INF_MARKER)

        f = FloatAttribute(None, allow_null=True)
        self.assertIsNone(f.value)

        with self.assertRaises(NullAttributeError):
            FloatAttribute(None)

    def test_positive_float_attribute(self):
        f = PositiveFloatAttribute(4.4)
        self.assertEqual(f.value, 4.4)
        self.assertDictEqual(
            f.to_dict(),
            {
                'attribute_type': PositiveFloatAttribute.typename,
                'value': 4.4
            }
        )
        with self.assertRaises(AttributeValueError):
            PositiveFloatAttribute(-3.2)

        with self.assertRaises(AttributeValueError):
            PositiveFloatAttribute(0)

        f = PositiveFloatAttribute(POSITIVE_INF_MARKER)
        self.assertEqual(f.value, POSITIVE_INF_MARKER)

        with self.assertRaises(AttributeValueError):
            f = PositiveFloatAttribute(NEGATIVE_INF_MARKER)

    def test_nonnegative_float_attribute(self):
        f = NonnegativeFloatAttribute(4.4)
        self.assertEqual(f.value, 4.4)
        self.assertDictEqual(
            f.to_dict(),
            {
                'attribute_type': NonnegativeFloatAttribute.typename,
                'value': 4.4
            }
        )
        f = NonnegativeFloatAttribute(0.0)
        self.assertEqual(f.value, 0.0)

        with self.assertRaises(AttributeValueError):
            NonnegativeFloatAttribute(-3.2)

        f = PositiveFloatAttribute(POSITIVE_INF_MARKER)
        self.assertEqual(f.value, POSITIVE_INF_MARKER)

        with self.assertRaises(AttributeValueError):
            f = PositiveFloatAttribute(NEGATIVE_INF_MARKER)

    def test_string_attribute(self):
        # this is sort of double test-coverage, but that can't hurt
        s = StringAttribute('abc')
        self.assertEqual(s.value, 'abc')
        self.assertDictEqual(
            s.to_dict(),
            {
                'attribute_type': StringAttribute.typename,
                'value': 'abc'
            }
        )

        s = StringAttribute('a string with space')
        self.assertEqual(s.value, 'a_string_with_space')
        self.assertDictEqual(
            s.to_dict(),
            {
                'attribute_type': StringAttribute.typename,
                'value': 'a_string_with_space'
            }
        )
        with self.assertRaises(AttributeValueError):
            StringAttribute('-9abc')

        with self.assertRaises(AttributeValueError):
            StringAttribute(3.4)

    def test_unrestrictedstring_attribute(self):
        # this is sort of double test-coverage, but that can't hurt
        s = UnrestrictedStringAttribute('-9abc')
        self.assertEqual(s.value, '-9abc')
        self.assertDictEqual(
            s.to_dict(),
            {
                'attribute_type': UnrestrictedStringAttribute.typename,
                'value': '-9abc'
            }
        )

        s = UnrestrictedStringAttribute('String with space')
        self.assertEqual(s.value, 'String with space')

        s = UnrestrictedStringAttribute(3.4)
        self.assertEqual(s.value, '3.4')

    def test_missing_keys_for_bounded_attributes(self):

        for clazz in [BoundedIntegerAttribute, BoundedFloatAttribute]:
            # test missing min key
            with self.assertRaises(MissingAttributeKeywordError):
                i = clazz(3, max=10)
        
            # test missing max key
            with self.assertRaises(MissingAttributeKeywordError):
                i = clazz(3, min=0)

            # test missing both keys
            with self.assertRaises(MissingAttributeKeywordError):
                i = clazz(3)

    def test_bounded_integer_attribute(self):

        # test a valid bounded int
        i = BoundedIntegerAttribute(3, min=0, max=5)
        self.assertEqual(i.value, 3)
        self.assertDictEqual(
            i.to_dict(),
            {
                'attribute_type': BoundedIntegerAttribute.typename,
                'value': 3,
                'min': 0,
                'max':5
            }
        )
        # within bounds, but a float
        with self.assertRaises(AttributeValueError):
            i = BoundedIntegerAttribute(3.3, min=0, max=5)

        # out of bounds (over)
        with self.assertRaises(AttributeValueError):
            i = BoundedIntegerAttribute(12, min=0, max=10)

        # out of bounds (under)
        with self.assertRaises(AttributeValueError):
            i = BoundedIntegerAttribute(-2, min=0, max=10)

        # out of bounds (under) AND wrong type
        with self.assertRaises(AttributeValueError):
            i = BoundedIntegerAttribute(-2.2, min=0, max=10)

        # bounds are wrong type.  Since we want an integer,
        # the bounds should be integers also.
        with self.assertRaises(InvalidAttributeKeywordError):
            i = BoundedIntegerAttribute(2, min=0.1, max=10)
        with self.assertRaises(InvalidAttributeKeywordError):
            i = BoundedIntegerAttribute(2, min=0, max=10.2)
        with self.assertRaises(InvalidAttributeKeywordError):
            i = BoundedIntegerAttribute(2, min=0.1, max=10.2)

        # out of bounds AND wrong type of bounds
        with self.assertRaises(InvalidAttributeKeywordError):
            i = BoundedIntegerAttribute(22, min=0.1, max=10.2)

        # can't use positive inf as a bound
        with self.assertRaises(InvalidAttributeKeywordError):
            i = BoundedIntegerAttribute(22, min=0, max=POSITIVE_INF_MARKER)

        # can't use inf as a value in a bounded int
        with self.assertRaises(AttributeValueError):
            i = BoundedIntegerAttribute(POSITIVE_INF_MARKER, min=0, max=100)

    def test_bounded_float_atttribute(self):

        # test a valid bounded float
        f = BoundedFloatAttribute(0.2, min=0, max=1.0)
        self.assertEqual(f.value, 0.2)
        self.assertDictEqual(
            f.to_dict(),
            {
                'attribute_type': BoundedFloatAttribute.typename,
                'value': 0.2,
                'min': 0.0,
                'max':1.0
            }
        )
        # within bounds, but int
        f = BoundedFloatAttribute(3.3, min=0, max=5)
        self.assertEqual(f.value, 3.3)

        # within bounds, equal to max
        f = BoundedFloatAttribute(5.0, min=0, max=5)
        self.assertEqual(f.value, 5.0)

        # out of bounds (over)
        with self.assertRaises(AttributeValueError):
            f = BoundedFloatAttribute(1.2, min=0, max=1.0)

        # out of bounds (under)
        with self.assertRaises(AttributeValueError):
            f = BoundedFloatAttribute(-2.2, min=0, max=10)

        # you CAN specify integer bounds for bounded floats
        f = BoundedFloatAttribute(2.2, min=0, max=10)
        f = BoundedFloatAttribute(2.2, min=0.2, max=10.5)

        # can't use positive inf as a bound
        with self.assertRaises(InvalidAttributeKeywordError):
            i = BoundedFloatAttribute(22, min=0, max=POSITIVE_INF_MARKER)

        # can't use inf as a value in a bounded float
        with self.assertRaises(AttributeValueError):
            i = BoundedFloatAttribute(POSITIVE_INF_MARKER, min=0, max=100)

    def test_boolean_attribute(self):
        '''
        Tests that a range of canonical values can be used to specify
        whether a boolean attribute is true or false.
        '''
        b = BooleanAttribute('true')
        self.assertTrue(b.value)
        self.assertDictEqual(
            b.to_dict(),
            {
                'attribute_type': BooleanAttribute.typename,
                'value': True
            }
        )
        b = BooleanAttribute('True')
        self.assertTrue(b.value)
        b = BooleanAttribute(1)
        self.assertTrue(b.value)
        b = BooleanAttribute(True)
        self.assertTrue(b.value)
        with self.assertRaises(AttributeValueError):
            b = BooleanAttribute(2)

        b = BooleanAttribute('false')
        self.assertFalse(b.value)
        b = BooleanAttribute('False')
        self.assertFalse(b.value)
        b = BooleanAttribute(0)
        self.assertFalse(b.value)
        b = BooleanAttribute(False)
        self.assertFalse(b.value)
        with self.assertRaises(AttributeValueError):
            b = BooleanAttribute(-1)

    def test_dataresource_attribute(self):
        '''
        Tests the various iterations of DataResourceAttribute classes, 
        which is used when specifying files for use in analysis `Operation`s.
        '''

        tested_classes = [
            DataResourceAttribute, 
            OperationDataResourceAttribute
        ]

        for clazz in tested_classes:

            # works:
            u = str(uuid.uuid4())
            d = clazz(u, many=True, resource_type='XYZ')
            self.assertDictEqual(
                d.to_dict(),
                {
                    'attribute_type': clazz.typename,
                    'value': u,
                    'many': True,
                    'resource_type': 'XYZ'
                }
            )
            d = clazz(str(uuid.uuid4()), many=False, resource_type='XYZ')
            d = clazz(str(uuid.uuid4()), many=1, resource_type='XYZ')

            # should fail since multiple UUID passed, but many=False
            with self.assertRaises(AttributeValueError):
                clazz(
                    [str(uuid.uuid4()), str(uuid.uuid4())], 
                    many=False,
                    resource_type='XYZ'
                )

            # should fail since one of the vals is NOT a UUID
            with self.assertRaises(AttributeValueError):
                clazz(
                    [str(uuid.uuid4()), 'abc'], 
                    many=True,
                    resource_type='XYZ'
                )

            # the "value" is not a UUID. Should fail:
            with self.assertRaises(AttributeValueError):
                clazz('abc', many=True, resource_type='XYZ')

            # missing the "many" key
            with self.assertRaises(MissingAttributeKeywordError):
                clazz(str(uuid.uuid4()), resource_type='XYZ')

    def test_variable_dataresource_attribute(self):
        '''
        Tests the VariableDataResourceAttribute classes, 
        which permits multiple resource types
        '''

        # works:
        u = str(uuid.uuid4())
        d = VariableDataResourceAttribute(
            u, many=True, resource_types=['XYZ'])
        self.assertDictEqual(
            d.to_dict(),
            {
                'attribute_type': VariableDataResourceAttribute.typename,
                'value': u,
                'many': True,
                'resource_types': ['XYZ']
            }
        )
        d = VariableDataResourceAttribute(
            str(uuid.uuid4()), many=False, resource_types=['XYZ'])

        # should fail since multiple UUID passed, but many=False
        with self.assertRaises(AttributeValueError):
            VariableDataResourceAttribute(
                [str(uuid.uuid4()), str(uuid.uuid4())], 
                many=False,
                resource_types=['XYZ']
            )

        # should fail since one of the vals is NOT a UUID
        with self.assertRaises(AttributeValueError):
            VariableDataResourceAttribute(
                [str(uuid.uuid4()), 'abc'], 
                many=True,
                resource_types=['XYZ']
            )

        # the "value" is not a UUID. Should fail:
        with self.assertRaises(AttributeValueError):
            VariableDataResourceAttribute('abc', 
                many=True, resource_types=['XYZ'])

        # missing the "many" key
        with self.assertRaisesRegex(MissingAttributeKeywordError, 'many'):
            VariableDataResourceAttribute(str(uuid.uuid4()), resource_types=['XYZ'])

        # missing the "resource_types" key since it's given as "resource_type"
        # (singular, no "s" at the end). Likely a common mistake
        with self.assertRaisesRegex(MissingAttributeKeywordError, 'resource_types'):
            VariableDataResourceAttribute(str(uuid.uuid4()), resource_type=['XYZ'])

        # The "resource_types" key is a string, not a list as required
        with self.assertRaisesRegex(InvalidAttributeKeywordError, 'list'):
            VariableDataResourceAttribute(str(uuid.uuid4()), 
                many=True, resource_types='XYZ')

    def test_option_string_attribute(self):

        # test that leaving out the 'options' key causes a problem
        with self.assertRaises(MissingAttributeKeywordError):
            s = OptionStringAttribute('abc')

        # test that a valid spec works
        s = OptionStringAttribute('abc', options=['xyz','abc'])
        self.assertEqual(s.value, 'abc')
        expected_dict_representation = {
            'attribute_type': 'OptionString', 
            'value': 'abc', 
            'options': ['xyz', 'abc']
        }
        self.assertDictEqual(expected_dict_representation, s.to_dict())

        # test that case matters
        with self.assertRaises(AttributeValueError):
            s = OptionStringAttribute('Abc', options=['xyz','abc'])

        # test null value when allowed:
        s = OptionStringAttribute(None, options=['xyz','abc'], allow_null=True)
        self.assertIsNone(s.value)

        # test that exception raised if value is not in the valid options
        with self.assertRaisesRegex(AttributeValueError, 'not among the valid options'):
            s = OptionStringAttribute('x', options=['xyz','abc'])

        # test that exception raised if options are not a list
        with self.assertRaisesRegex(InvalidAttributeKeywordError, 'list'):
            s = OptionStringAttribute('abc', options='abc')
        with self.assertRaisesRegex(InvalidAttributeKeywordError, 'list'):
            s = OptionStringAttribute('abc', options={})

        # test that exception raised if value if one of the options is
        # not a string. The value is valid against one of the options, but
        # we require everything to be perfect.
        with self.assertRaisesRegex(InvalidAttributeKeywordError, 
            'need to be strings'):
            s = OptionStringAttribute('xyz', options=['xyz',1,'abc'])