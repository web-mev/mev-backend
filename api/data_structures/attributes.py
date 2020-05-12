from rest_framework.exceptions import ValidationError

import api.utilities as api_utils
import api.exceptions as api_exceptions


class BaseAttribute(object):
    '''
    Base object which defines some common methods and members
    for Attribute types

    Classes that derive from `BaseAttribute` have strings which
    identify their type (`typename`) and a `value`, which is specific
    to the child class implementation.  See child classes for 
    examples.
    '''
    typename = None

    def __init__(self, value, **kwargs):
        self.value_validator(value)
        
        # if kwargs is not an empty dict, raise an exception
        if kwargs != {}:
            raise ValidationError('This type of attribute does not '
            ' accept additional keyword arguments.'
            ' Received: {keys}'.format(keys=','.join(kwargs.keys())))

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


class BoundedBaseAttribute(BaseAttribute):
    '''
    This class derives from `BaseAttribute` and adds
    logic for numeric attributes that are bounded between
    specified values.

    In addition to the `typename` and `value` members, these
    require a `min` and a `max` to set the bounds.

    Classes deriving from this can be used for things like bounding
    a p-value from a hypothesis test (which is 0<=p<=1)
    '''
    MINIMUM_KEY = 'min'
    MAXIMUM_KEY = 'max'

    def __init__(self, value, **kwargs):
        try: 
            self.min_value = kwargs[self.MINIMUM_KEY]
            self.max_value = kwargs[self.MAXIMUM_KEY]
        except KeyError as ex:
            missing_key = str(ex)
            raise ValidationError('Need bounds to specify a BoundedInteger.'
                ' Was missing {key}'.format(key=missing_key))
        super().__init__(value)

    def check_bound_types(self, primitive_type_list):
        '''
        This checks that the bounds are sensible for the specific
        implementation of the bounded type.  For example, if we are
        creating a bounded integer, the bounds are also integers.
        
        The child implementations call this and provide the 
        acceptable types as a list.
        '''
        d = {
            'minimum': self.min_value,
            'maximum': self.max_value
        }
        for k in d.keys():
            dtype = type(d[k])
            if not dtype in primitive_type_list:
                raise ValidationError('The {bound} value {val}'
                ' specified does not match the expected type'
                ' for this bounded attribute.'.format(
                    bound=k,
                    val = d[k]
                ))

    def to_representation(self):
        return {
            'attribute_type': self.typename,
            'value': self.value,
            self.MINIMUM_KEY: self.min_value,
            self.MAXIMUM_KEY: self.max_value,
        }

    def __repr__(self):
        return '{val} ({typename}:[{min_val},{max_val}])'.format(
            val=self.value,
            typename=self.typename,
            min_val = self.min_value,
            max_val = self.max_value,
        )

class IntegerAttribute(BaseAttribute):
    '''
    General, unbounded integers.  Represented by
    ```
    {
        "attribute_type": "Integer",
        "value": <integer>
    }
    ```
    '''

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
    '''
    Integers > 0
    ```
    {
        "attribute_type": "PositiveInteger",
        "value": <integer>
    }
    ```
    '''
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
    '''
    Integers >=0
    ```
    {
        "attribute_type": "NonNegativeInteger",
        "value": <integer>
    }
    ```
    '''
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


class BoundedIntegerAttribute(BoundedBaseAttribute):
    '''
    Integers that are bounded between a min and max value.
    ```
    {
        "attribute_type": "BoundedInteger",
        "value": <integer>,
        "min": <integer lower bound>,
        "max": <integer upper bound>
    }
    ```
    '''
    typename = 'BoundedInteger'

    def value_validator(self, val):

        # here we also validate that the bounds are of
        # the same integer type
        self.check_bound_types([int])

        if type(val) == int:
            if (val >= self.min_value) and (val <= self.max_value):
                self.value = val
            else:
                raise ValidationError(
                    'The value {val} is not within the bounds' 
                    ' of [{min},{max}]'.format(
                        val=val,
                        min=self.min_value,
                        max=self.max_value)
                    )    
        else:
            raise ValidationError(
                'A bounded integer attribute was expected,'
                ' but "{val}" is not an integer.'.format(val=val))


class FloatAttribute(BaseAttribute):
    '''
    General, unbounded float type
    ```
    {
        "attribute_type": "Float",
        "value": <float>
    }
    ```
    '''
    typename = 'Float'

    def value_validator(self, val):
        if (type(val) == float) or (type(val) == int):
            self.value = float(val)
        else:
            raise ValidationError(
                'A float attribute was expected, but'
                ' received "{val}"'.format(val=val))


class PositiveFloatAttribute(BaseAttribute):
    '''
    Positive (>0) float type
    ```
    {
        "attribute_type": "PositiveFloat",
        "value": <float>
    }
    ```
    '''
    typename = 'PositiveFloat'

    def value_validator(self, val):
        
        if (type(val) == float) or (type(val) == int):
            if val > 0:
                self.value = float(val)
            else:
                raise ValidationError('Received a valid float, but'
                    ' it was not > 0.')
        else:
            raise ValidationError(
                'A float attribute was expected, but'
                ' received "{val}"'.format(val=val))


class NonnegativeFloatAttribute(BaseAttribute):
    '''
    Non-negative (>=0) float type
    ```
    {
        "attribute_type": "NonNegativeFloat",
        "value": <float>
    }
    ```
    '''
    typename = 'NonNegativeFloat'

    def value_validator(self, val):
        
        if (type(val) == float) or (type(val) == int):
            if val >= 0:
                self.value = float(val)
            else:
                raise ValidationError('Received a valid float, but'
                    ' it was not >= 0.')
        else:
            raise ValidationError(
                'A float attribute was expected, but'
                ' received "{val}"'.format(val=val))

class BoundedFloatAttribute(BoundedBaseAttribute):
    '''
    Floats that are bounded between a min and max value.
    ```
    {
        "attribute_type": "BoundedFloat",
        "value": <float>,
        "min": <integer/float lower bound>,
        "max": <integer/float upper bound>
    }
    ```
    '''
    typename = 'BoundedFloat'

    def value_validator(self, val):

        # here we also validate that the bounds are of
        # the same integer type
        self.check_bound_types([int, float])

        if (type(val) == float) or (type(val) == int):
            if (val >= self.min_value) and (val <= self.max_value):
                self.value = val
            else:
                raise ValidationError(
                    'The value {val} is not within the bounds' 
                    ' of [{min},{max}]'.format(
                        val=val,
                        min=self.min_value,
                        max=self.max_value)
                    )    
        else:
            raise ValidationError(
                'A bounded float attribute was expected,'
                ' but "{val}" is not a float.'.format(val=val))


class StringAttribute(BaseAttribute):
    '''
    String type that has basic guards against
    non-typical characters.
    ```
    {
        "attribute_type": "String",
        "value": <str>
    }
    ```
    '''
    typename = 'String'

    def value_validator(self, val):
        try:
            val = api_utils.normalize_identifier(val)
            self.value = val
        except api_exceptions.StringIdentifierException as ex:
            raise ValidationError(str(ex))


# collect the types into logical groupings so we can 
# map the typenames (e.g. "PositiveFloat") to their
# class implementation
numeric_attribute_types = [
    IntegerAttribute,
    PositiveIntegerAttribute,
    NonnegativeIntegerAttribute,
    FloatAttribute,
    BoundedIntegerAttribute,
    BoundedFloatAttribute
]
numeric_attribute_typenames = [x.typename for x in numeric_attribute_types]
all_attribute_types = numeric_attribute_types + [StringAttribute,]
all_attribute_typenames = [x.typename for x in all_attribute_types]
attribute_mapping = dict(zip(all_attribute_typenames, all_attribute_types))


def create_attribute(attr_key, attribute_dict):
    '''
    Utility function used by the serializers to create/return
    BaseAttribute-derived instances.

    Accepts an `attribute_dict` which is a Python dictionary object
    containing the keys appropriate to create a particular attribute.
    For example, to create a `BoundedIntegerAttribute`, this dict would
    be formatted as,
    ```
    attr_dict = {
        'attribute_type': 'BoundedInteger',
        'value': 3,
        'min': 0,
        'max': 10
    }
    ```
    '''
    attr_dict = attribute_dict.copy()
    try:
        attr_val = attr_dict.pop('value')
    except KeyError as ex:
        raise ValidationError({attr_key: 'Attributes must supply'
        ' a "value" key.'})

    try:
        attribute_typename = attr_dict.pop('attribute_type')
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
    # If the specification is not correct, it will raise an exception.
    # Note that there may be additional kwargs (other than value and attribute_type)
    # that were passed, such as for specifying the bounds on bounded attributes.
    # Need to pass those through.  Since we popped keys off the initial dictionary
    # only the "additional" keyword entries are left in `attr_dict`
    try:
        attribute_instance = attribute_type(attr_val, **attr_dict)
    except ValidationError as ex:
        raise ValidationError({
            attr_key: ex.detail
        })
    return attribute_instance