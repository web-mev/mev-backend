import re
import uuid
import logging

from django.conf import settings

import api.utilities as api_utils
from api.exceptions import StringIdentifierException, \
    AttributeValueError, \
    InvalidAttributeKeywords

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
                raise AttributeValueError('Received a null/None value which is not allowed.')

        # if kwargs is not an empty dict, raise an exception
        if kwargs != {}:
            raise AttributeValueError('This type of attribute does not '
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
            raise InvalidAttributeKeywords('The parameters for this attribute'
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
            raise AttributeValueError('Need bounds to specify a BoundedInteger.'
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
                raise AttributeValueError('The {bound} value {val}'
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
            raise AttributeValueError(
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
                raise AttributeValueError(
                    'The value {val} was not a' 
                    ' positive integer.'.format(val=val))    
        else:
            raise AttributeValueError(
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
                raise AttributeValueError(
                    'The value {val} is not a non-' 
                    'negative integer.'.format(val=val))    
        else:
            raise AttributeValueError(
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
                raise AttributeValueError(
                    'The value {val} is not within the bounds' 
                    ' of [{min},{max}]'.format(
                        val=val,
                        min=self.min_value,
                        max=self.max_value)
                    )    
        else:
            raise AttributeValueError(
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
            raise AttributeValueError(
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
                raise AttributeValueError('Received a valid float, but'
                    ' it was not > 0.')
        elif val == settings.POSITIVE_INF_MARKER:
            self.value = val
        else:
            raise AttributeValueError(
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
                raise AttributeValueError('Received a valid float, but'
                    ' it was not >= 0.')
        elif val == settings.POSITIVE_INF_MARKER:
            self.value = val
        else:
            raise AttributeValueError(
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
                raise AttributeValueError(
                    'The value {val} is not within the bounds' 
                    ' of [{min},{max}]'.format(
                        val=val,
                        min=self.min_value,
                        max=self.max_value)
                    ) 
        else:
            raise AttributeValueError(
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
        except StringIdentifierException as ex:
            raise AttributeValueError(str(ex))

class UnrestrictedStringAttribute(BaseAttribute):
    '''
    String type that doesn't check for spacing, etc.
    ```
    {
        "attribute_type": "UnrestrictedString",
        "value": <str>
    }
    ```
    '''
    typename = 'UnrestrictedString'

    def value_validator(self, val, set_value=True, allow_null=False):
        if set_value:
            self.value = str(val)


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
                        raise InvalidAttributeKeywords('The options need to be strings. Failed on validating: {x}'.format(
                            x = opt)
                    )
                self.options = options
            else:
                raise InvalidAttributeKeywords('Need to supply a list with the {opts} key.'.format(
                    opts = self.OPTIONS_KEY)
                )
        except KeyError as ex:
            missing_key = str(ex)
            raise InvalidAttributeKeywords('Need a list of options to specify an OptionStringAttribute.'
                ' Was missing {key}'.format(key=missing_key))

    def value_validator(self, val, set_value=True, allow_null=False):
        if (val is None) and (not allow_null):
            raise AttributeValueError('Cannot set this to be null/None.')
        
        if not val in self.options:
            raise AttributeValueError('The value "{val}" was not among the valid options: {opts}'.format(
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
            raise AttributeValueError(
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
                raise AttributeValueError('The values ({val})'
                    ' are inconsistent with the many=False'
                    ' parameter.'.format(
                        val=val
                    )
                )
            all_vals = val
        else:
            raise AttributeValueError('Value needs to be either'
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
                raise AttributeValueError('The passed value ({val}) was'
                    ' not a valid UUID.'.format(val=v)
                )
            except Exception as ex:
                raise AttributeValueError('Encountered an unknown exception'
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


class OperationDataResourceAttribute(DataResourceAttribute):
    '''
    Used to specify a reference to one or more Resource
    instances which are user-independent, such as database-like 
    resources which are used for analyses.
    ```
    {
        "attribute_type": "OperationDataResource",
        "value": <one or more Resource UUIDs>,
        "many": <bool>,
    }
    ```
    Note that "many" controls whether >1 are allowed. It's not an indicator
    for whether there are multiple Resources specified in the "value" key.
    '''
    typename = 'OperationDataResource'


class VariableDataResourceAttribute(DataResourceAttribute):
    '''
    This class is a specialization of a DataResource which functions to allow
    variable output resource types.

    The reason for this is as follows:
    In earlier iterations of WebMeV, the "type" of output files was fixed; for instance, 
    differential expression analyses always produced 'feature tables'. However, some 
    WebMeV `Operations` perform simple operations such as renaming rows (e.g.
    changing gene names from ENSG to symbols) which can work with multiple file types.
    The fixed system did not allow for such a general tool; we would have to create a 
    virtually identical tool for each type of input file that we want to handle. 
    That's obviously not ideal. Instead, we would like to allow those `Operation`s to 
    create files that have the same type as the input file (e.g. an input feature table 
    would create an output feature table).

    The `VariableDataResource` type is a signal to the code that handles the finalization
    of `ExecutedOperation`s that it should expect an output file that can have multiple types.
    The actual type will be set by the `ExecutedOperation` in its `outputs.json` file. However,
    those details are handled in the "operation spec" classes, not here. This class just establishes
    this as an available type.
    '''
    typename = 'VariableDataResource'


def convert_dtype(dtype_str, **kwargs):
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
        if 'allow_unrestricted_strings' in kwargs:
            return UnrestrictedStringAttribute.typename
        return StringAttribute.typename