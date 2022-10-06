import unittest
import uuid


from data_structures.data_resource_attributes import DataResourceAttribute, \
    VariableDataResourceAttribute, \
    OperationDataResourceAttribute

from exceptions import AttributeValueError, \
    InvalidAttributeKeywordError, \
    MissingAttributeKeywordError, \
    InvalidResourceTypeException


class TestDataresourceAttributes(unittest.TestCase):

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

    def test_resource_type_setter(self):
        '''
        For both DataResourceAttribute and VariableDataResourceAttribute,
        check that the setters work as intended
        '''

        d = DataResourceAttribute(str(uuid.uuid4()), 
            many=True, resource_type='XYZ')
        # now set and check:
        d.resource_type = 'foo'
        self.assertEqual('foo', d.resource_type)

        d = VariableDataResourceAttribute(str(uuid.uuid4()), 
            many=True, resource_types=['XYZ', 'ABC'])
        d.resource_types = ['DEF']
        self.assertCountEqual(d.resource_types, ['DEF'])

        # try setting to a non-list:
        with self.assertRaisesRegex(InvalidAttributeKeywordError, 'requires a list'):
            d.resource_types = 'xyz'


    def test_dataresource_type_validation(self):
        '''
        While the data structures are agnostic to the actual resource types of WebMeV
        (e.g. numeric matrix is "MTX"), we provide a 
        validation method which is called with the permissible types.

        Note that the method ALSO functions as a way to check if a submitted
        input (by a user wishing to run a job) corresponds to a resource
        with the proper resource type
        '''

        # although redundant, make a specific test that is 
        # similar to our usage of the method for validating a user
        # input
        d = DataResourceAttribute(str(uuid.uuid4()), 
            many=True, resource_type='XYZ')
        d.check_resource_type_keys(['XYZ'])

        # this works:
        d = DataResourceAttribute(str(uuid.uuid4()), 
            many=True, resource_type='XYZ')
        permissible_types = set(['abc', 'XYZ'])
        d.check_resource_type_keys(permissible_types)

        # this fails:
        permissible_types = set(['abc', 'def'])
        with self.assertRaisesRegex(InvalidResourceTypeException, 'XYZ'):
            d.check_resource_type_keys(permissible_types)

        # this works:
        d = OperationDataResourceAttribute(str(uuid.uuid4()), 
            many=True, resource_type='XYZ')
        permissible_types = set(['abc', 'XYZ'])
        d.check_resource_type_keys(permissible_types)

        # this fails:
        permissible_types = set(['abc', 'def'])
        with self.assertRaisesRegex(InvalidResourceTypeException, 'XYZ'):
            d.check_resource_type_keys(permissible_types)

        # this works:
        d = VariableDataResourceAttribute(str(uuid.uuid4()), 
            many=True, resource_types=['ABC', 'DEF'])
        permissible_types = set(['ABC', 'DEF', 'XYZ'])
        d.check_resource_type_keys(permissible_types)

        # this fails:
        permissible_types = set(['ABC', 'GHI'])
        with self.assertRaisesRegex(InvalidResourceTypeException, 'DEF'):
            d.check_resource_type_keys(permissible_types)

