from rest_framework.exceptions import ValidationError

import api.utilities as api_utils
import api.exceptions as api_exceptions


class BaseAttribute(object):
    '''
    Base object which defines some common behavior for Attribute types
    '''
    typename = None

    def __init__(self, value):
        self.value_validator(value)

    def value_validator(self, val):
        raise NotImplementedError('You must override this method.')

    def to_representation(self):
        return {
            'attribute_type': self.typename,
            'value': self.value
        }

    def __eq__(self, other):
        same_type = self.typename == other.typename
        same_val = self.value == other.value
        return all([same_type, same_val])

    def __repr__(self):
        return '{val} ({typename})'.format(
            val=self.value,
            typename=self.typename
        )


class IntegerAttribute(BaseAttribute):

    typename = 'Integer'

    def value_validator(self, val):
        if type(val) == int:
            self.value = val
        else:
            raise ValidationError(
                'An integer attribute was expected, but the'
                ' value "{val}" could not'
                ' be cast as an integer'.format(val=val)
            )

class PositiveIntegerAttribute(BaseAttribute):

    typename = 'PositiveInteger'

    def value_validator(self, val):
        if type(val) == int:
            if val > 0:
                self.value = val
            else:
                raise ValidationError(
                    'The value {val} was not a' 
                    ' positive integer.'.format(val=val))    
        else:
            raise ValidationError(
                'A positive integer attribute was expected,'
                ' but "{val}" is not.'.format(val=val))


class NonnegativeIntegerAttribute(BaseAttribute):

    typename = 'NonNegativeInteger'

    def value_validator(self, val):
        if type(val) == int:
            if val >= 0:
                self.value = val
            else:
                raise ValidationError(
                    'The value {val} is not a non-' 
                    'negative integer.'.format(val=val))    
        else:
            raise ValidationError(
                'A non-negative integer attribute was expected,'
                ' but "{val}" is not.'.format(val=val))

#TODO: implement a bounded int

class FloatAttribute(BaseAttribute):

    typename = 'Float'

    def value_validator(self, val):
        if (type(val) == float) or (type(val) == int):
            self.value = float(val)
        else:
            raise ValidationError(
                'A float attribute was expected, but'
                ' received "{val}"'.format(val=val))

#TODO: implement a positive float
#TODO: implement a bounded float


class StringAttribute(BaseAttribute):

    typename = 'String'

    def value_validator(self, val):
        try:
            val = api_utils.normalize_identifier(val)
            self.value = val
        except api_exceptions.StringIdentifierException as ex:
            raise ValidationError(str(ex))

    
numeric_attribute_types = [
    IntegerAttribute,
    PositiveIntegerAttribute,
    NonnegativeIntegerAttribute,
    FloatAttribute
]
numeric_attribute_typenames = [x.typename for x in numeric_attribute_types]

all_attribute_types = numeric_attribute_types + [StringAttribute,]
all_attribute_typenames = [x.typename for x in all_attribute_types]

attribute_mapping = dict(zip(all_attribute_typenames, all_attribute_types))

def create_attribute(attr_key, attr_dict):

    try:
        attr_val = attr_dict['value']
    except KeyError as ex:
        raise ValidationError({attr_key: 'Attributes must supply'
        ' a "value" key.'})

    try:
        attribute_typename = attr_dict['attribute_type']
    except KeyError as ex:
        raise ValidationError({attr_key: 'Attributes must supply'
        ' an "attribute_type" key.'})

    if not attribute_typename in all_attribute_typenames:
        raise ValidationError({attr_dict:'Attributes must supply'
        ' a valid "attribute_type" from the choices of: {typelist}'.format(
            typelist='\n'.join(all_attribute_typenames)
        )})
    attribute_type = attribute_mapping[attribute_typename]

    # we "test" validity by trying to create an Attribute subclass instance.
    # If the specification is not correct, it will raise an exception
    try:
        attribute_instance = attribute_type(attr_val)
    except ValidationError as ex:
        raise ValidationError({
            attr_key: ex.detail
        })
    return attribute_instance