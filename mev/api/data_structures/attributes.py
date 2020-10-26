import re
import uuid
import logging

from django.conf import settings
from rest_framework.exceptions import ValidationError

import api.utilities as api_utils
import api.exceptions as api_exceptions

logger = logging.getLogger(__name__)

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

    # add any additional parameters (which are specified as kwargs to the
    # constructor) to this list.
    REQUIRED_PARAMS = []

    def __init__(self, value, **kwargs):
        # set to None so we do not get attribute errors:
        self.value = None

        # do we allow null/NaN? If not explicitly given, assume we do NOT allow nulls
        try:
            allow_null = bool(kwargs.pop('allow_null'))
        except KeyError:
            allow_null = False

        # are we setting the value, or just using the constructor as a way to 
        # validate?
        try:
            set_value = bool(kwargs.pop('set_value'))
        except KeyError:
            set_value = True

        # go ahead and validate if we do have a value to check
        if value is not None:
            self.value_validator(value, allow_null=allow_null, set_value=set_value)
        else:
            # value is None...is that ok? If not, raise an exception
            if not allow_null:
                raise ValidationError('Received a null/None value which is not allowed.')

        # if kwargs is not an empty dict, raise an exception
        if kwargs != {}:
            raise ValidationError('This type of attribute does not '
            ' accept additional keyword arguments.'
            ' Received: {keys}'.format(keys=','.join(kwargs.keys())))

    def value_validator(self, val, set_value=True, allow_null=False):
        raise NotImplementedError('You must override this method.')

    def check_keys(self, keys):
        '''
        Given a list of provided parameters (`keys`),
        check this against the required parameters for the
        attribute class.
        '''
        s1 = set(keys)
        if not s1 == set(self.REQUIRED_PARAMS):
            raise ValidationError('The parameters for this attribute'
                ' ({given_keys}) do not match the required parameters:'
                ' {required_keys}'.format(
                    required_keys = ', '.join(self.REQUIRED_PARAMS),
                    given_keys = ', '.join(keys),
                )
            )

    def to_dict(self):
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

    # add any additional parameters (which are specified as kwargs to the
    # constructor) to this list.
    REQUIRED_PARAMS = [MINIMUM_KEY, MAXIMUM_KEY]

    def __init__(self, value, **kwargs):
        self.set_bounds(kwargs)
        super().__init__(value, **kwargs)

    def set_bounds(self, kwargs_dict):
        try: 
            self.min_value = kwargs_dict.pop(self.MINIMUM_KEY)
            self.max_value = kwargs_dict.pop(self.MAXIMUM_KEY)
        except KeyError as ex:
            missing_key = str(ex)
            raise ValidationError('Need bounds to specify a BoundedInteger.'
                ' Was missing {key}'.format(key=missing_key))

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

    def to_dict(self):
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

    def value_validator(self, val, set_value=True, allow_null=False):
        if type(val) == int:
            if set_value:
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

    def value_validator(self, val, set_value=True, allow_null=False):
        if type(val) == int:
            if val > 0:
                if set_value:
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

    def value_validator(self, val, set_value=True, allow_null=False):
        if type(val) == int:
            if val >= 0:
                if set_value:
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

    def value_validator(self, val, set_value=True, allow_null=False):

        # here we also validate that the bounds are of
        # the same integer type
        self.check_bound_types([int])

        if type(val) == int:
            if (val >= self.min_value) and (val <= self.max_value):
                if set_value:
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

    def value_validator(self, val, set_value=True, allow_null=False):
        if (type(val) == float) or (type(val) == int):
            if set_value:
                self.value = float(val)
        elif (val == settings.POSITIVE_INF_MARKER) or (val == settings.NEGATIVE_INF_MARKER):
            if set_value:
                self.value = val
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

    def value_validator(self, val, set_value=True, allow_null=False):
        
        if (type(val) == float) or (type(val) == int):
            if val > 0:
                if set_value:
                    self.value = float(val)
            else:
                raise ValidationError('Received a valid float, but'
                    ' it was not > 0.')
        elif val == settings.POSITIVE_INF_MARKER:
            self.value = val
        else:
            raise ValidationError(
                'A positive float attribute was expected, but'
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

    def value_validator(self, val, set_value=True, allow_null=False):
        
        if (type(val) == float) or (type(val) == int):
            if val >= 0:
                if set_value:
                    self.value = float(val)
            else:
                raise ValidationError('Received a valid float, but'
                    ' it was not >= 0.')
        elif val == settings.POSITIVE_INF_MARKER:
            self.value = val
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

    def value_validator(self, val, set_value=True, allow_null=False):

        # here we also validate that the bounds are of
        # the same integer type
        self.check_bound_types([int, float])

        if (type(val) == float) or (type(val) == int):
            if (val >= self.min_value) and (val <= self.max_value):
                if set_value:
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
                ' but "{val}" is not a float, or is not bounded.'.format(val=val))


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

    def value_validator(self, val, set_value=True, allow_null=False):
        try:
            val = api_utils.normalize_identifier(val)
            if set_value:
                self.value = val
        except api_exceptions.StringIdentifierException as ex:
            raise ValidationError(str(ex))


class OptionStringAttribute(BaseAttribute):
    '''
    A String type that only admits one from a set of preset options
    (e.g. like a dropdown)
    ```
    {
        "attribute_type": "OptionString",
        "value": <str>,
        "options": [<str>, <str>,...,<str>]
    }
    ```
    '''
    typename = 'OptionString'
    OPTIONS_KEY = 'options'
    REQUIRED_PARAMS = [OPTIONS_KEY, ]

    def __init__(self, value, **kwargs):
        self._set_options(kwargs)
        super().__init__(value, **kwargs)

    def _set_options(self, kwargs_dict):
        try:
            options = kwargs_dict.pop(self.OPTIONS_KEY)
            if type(options) == list:
                for opt in options:
                    if not type(opt) == str:
                        raise ValidationError('The options need to be strings. Failed on validating: {x}'.format(
                            x = opt)
                    )
                self.options = options
            else:
                raise ValidationError('Need to supply a list with the {opts} key.'.format(
                    opts = self.OPTIONS_KEY)
                )
        except KeyError as ex:
            missing_key = str(ex)
            raise ValidationError('Need a list of options to specify an OptionStringAttribute.'
                ' Was missing {key}'.format(key=missing_key))

    def value_validator(self, val, set_value=True, allow_null=False):
        if (val is None) and (not allow_null):
            raise ValidationError('Cannot set this to be null/None.')
        
        if not val in self.options:
            raise ValidationError('The value "{val}" was not among the valid options: {opts}'.format(
                val = val,
                opts = ','.join(self.options)
            ))
        elif set_value:
            self.value = val

    def to_dict(self):
        d = super().to_dict()
        d[self.OPTIONS_KEY] = self.options
        return d


class BooleanAttribute(BaseAttribute):
    '''
    Basic boolean
    ```
    {
        "attribute_type": "Boolean",
        "value": <bool>
    }
    ```
    '''
    typename = 'Boolean'

    def value_validator(self, val, set_value=True, allow_null=False):
        '''
        Validates that the value can be interpreted
        as a boolean.  Either true/false or 1/0
        '''
        val_type = type(val)
        final_val = None
        if val_type == str:
            if val.lower() in ['true', 'false']:
                final_val = val.lower()
        elif val_type == bool:
            final_val = val
        elif val_type == int:
            if val in [0,1]:
                final_val = val

        if final_val is not None:
            if final_val in ['true', 1, True]:
                if set_value:
                    self.value = True
            elif final_val in ['false', 0, False]:
                if set_value:
                    self.value = False
            else:
                raise Exception('Hit an edge case when trying to validate'
                    ' boolean value.  Value was {val} and the "final value"'
                    ' was {final_val}'.format(
                        val = val,
                        final_val = final_val
                    )
                )
        else:
            raise ValidationError(
                'A boolean attribute was expected,'
                ' but "{val}" cannot be interpreted as such.'.format(val=val)) 


class DataResourceAttribute(BaseAttribute):
    '''
    Used to specify a reference to one or more Resource
    instances.
    ```
    {
        "attribute_type": "DataResource",
        "value": <one or more Resource UUIDs>,
        "many": <bool>,
    }
    ```
    Note that "many" controls whether >1 are allowed. It's not an indicator
    for whether there are multiple Resources specified in the "value" key.
    '''
    typename = 'DataResource'

    MANY_KEY = 'many'
    REQUIRED_PARAMS = [MANY_KEY,]

    def __init__(self, value, **kwargs):
        self.check_keys(kwargs.keys())
        self.validate_many_key(kwargs.pop(self.MANY_KEY))
        super().__init__(value, **kwargs)
        
    def validate_many_key(self, v):
        '''
        Checks that the value passed can be cast as a proper boolean 
        '''
        # use the BooleanAttribute to validate:
        b = BooleanAttribute(v)
        self.many = b.value

    def value_validator(self, val, set_value=True, allow_null=False):
        '''
        Validates that the value (or values)
        are proper UUIDs. 
        '''
        # if a single UUID was passed, place it into a list:
        
        if (type(val) == str) or (type(val) == uuid.UUID):
            all_vals = [val,]
        elif type(val) == list:
            if self.many == False:
                raise ValidationError('The values ({val})'
                    ' are inconsistent with the many=False'
                    ' parameter.'.format(
                        val=val
                    )
                )
            all_vals = val
        else:
            raise ValidationError('Value needs to be either'
                ' a single UUID or a list of UUIDs'
            )

        try:
            all_vals = [str(x) for x in all_vals]
        except Exception as ex:
            logger.error('An unexpected exception occurred when trying'
                ' to validate a DataResource attribute.'
            )
            raise ex

        for v in all_vals:
            try:
                # check that it is a UUID
                # Note that we can't explicitly check that a UUID
                # corresponds to a Resource database instance
                # as that creates a circular import dependency.
                uuid.UUID(v)
            except ValueError as ex:
                raise ValidationError('The passed value ({val}) was'
                    ' not a valid UUID.'.format(val=v)
                )
            except Exception as ex:
                raise ValidationError('Encountered an unknown exception'
                    ' when validating a DataResourceAttribute instance. Value was'
                    ' {value}'.format(
                        value = v
                    )
                )
        
        if set_value:
            self.value = val

    def to_dict(self):
        d = super().to_dict()
        d[self.MANY_KEY] = self.many
        return d

# collect the types into logical groupings so we can 
# map the typenames (e.g. "PositiveFloat") to their
# class implementation
numeric_attribute_types = [
    IntegerAttribute,
    PositiveIntegerAttribute,
    NonnegativeIntegerAttribute,
    FloatAttribute,
    BoundedIntegerAttribute,
    BoundedFloatAttribute,
    PositiveFloatAttribute,
    NonnegativeFloatAttribute,
]
numeric_attribute_typenames = [x.typename for x in numeric_attribute_types]
other_attribute_types = [StringAttribute, BooleanAttribute, DataResourceAttribute, OptionStringAttribute]
all_attribute_types = numeric_attribute_types + other_attribute_types
all_attribute_typenames = [x.typename for x in all_attribute_types]
attribute_mapping = dict(zip(all_attribute_typenames, all_attribute_types))


def create_attribute(attr_key, attribute_dict, allow_null=False):
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
        raise ValidationError({attr_key:'Attributes must supply'
        ' a valid "attribute_type" from the choices of: {typelist}'.format(
            typelist=', '.join(all_attribute_typenames)
        )})
    attribute_type = attribute_mapping[attribute_typename]

    if allow_null:
        attr_dict['allow_null'] = True

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


def convert_dtype(dtype_str):
    '''
    Takes a pandas/numpy dtype and returns an appropriate attribute "type"
    string.  For instance, if "int64", return Integer.

    Since this function does not have any concept of bounding, etc. it will
    only return the most basic types like Integer, Float, and String
    '''

    if re.match('int\d{0,2}', dtype_str):
        return IntegerAttribute.typename
    elif re.match('float\d{0,2}', dtype_str):
        return FloatAttribute.typename
    else:
        return StringAttribute.typename