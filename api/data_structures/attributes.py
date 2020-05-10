from rest_framework import serializers

import api.utilities as api_utils
import api.exceptions as api_exceptions

class BaseAttribute(object):
    '''
    Base object which defines some common behavior for Attribute types
    '''
    typename = None

    def __init__(self, key, value):
        self.key_validator(key)
        self.value_validator(value)

    def key_validator(self, key):
        valid_key = api_utils.normalize_identifier(key)
        self.key = valid_key

    def value_validator(self, val):
        raise NotImplementedError('You must override this method.')


class IntegerAttribute(BaseAttribute):

    typename = 'Integer'

    def value_validator(self, val):
        if type(val) == int:
            self.value = val
        else:
            raise serializers.ValidationError({self.key:
                'An integer attribute was expected, but the'
                ' value "{val}" could not'
                ' be cast as an integer'.format(val=val)}
            )

class PositiveIntegerAttribute(BaseAttribute):

    typename = 'PositiveInteger'

    def value_validator(self, val):
        if type(val) == int:
            if val > 0:
                self.value = val
            else:
                raise serializers.ValidationError({self.key:
                    'The value {val} was not a' 
                    ' positive integer.'.format(val=val)})    
        else:
            raise serializers.ValidationError({self.key:
                'A positive integer attribute was expected,'
                ' but "{val}" is not.'.format(val=val)})


class NonnegativeIntegerAttribute(BaseAttribute):

    typename = 'NonNegativeInteger'

    def value_validator(self, val):
        if type(val) == int:
            if val >= 0:
                self.value = val
            else:
                raise serializers.ValidationError({self.key:
                    'The value {val} is not a non-' 
                    'negative integer.'.format(val=val)})    
        else:
            raise serializers.ValidationError({self.key:
                'A non-negative integer attribute was expected,'
                ' but "{val}" is not.'.format(val=val)})

#TODO: implement a bounded int

class FloatAttribute(BaseAttribute):

    typename = 'Float'

    def value_validator(self, val):
        if (type(val) == float) or (type(val) == int):
            self.value = float(val)
        else:
            raise serializers.ValidationError({self.key:
                'A float attribute was expected, but'
                ' received "{val}"'.format(val=val)})

#TODO: implement a positive float
#TODO: implement a bounded float


class StringAttribute(BaseAttribute):

    typename = 'String'

    def value_validator(self, val):
        try:
            val = api_utils.normalize_identifier(val)
            self.value = val
        except api_exceptions.StringIdentifierException as ex:
            raise serializers.ValidationError({self.key:str(ex)})

    