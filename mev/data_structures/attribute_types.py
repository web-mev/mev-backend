import uuid
import logging

from constants import POSITIVE_INF_MARKER, NEGATIVE_INF_MARKER

from helpers import normalize_identifier
from exceptions import NullAttributeError, \
    StringIdentifierException, \
    AttributeValueError, \
    InvalidAttributeKeywordError, \
    MissingAttributeKeywordError
from data_structures.base_attribute import BaseAttributeType

logger = logging.getLogger(__name__)


class BoundedBaseAttribute(BaseAttributeType):
    '''
    This class derives from `BaseAttributeType` and adds
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
        self._set_bounds(kwargs)
        super().__init__(value, **kwargs)

    def _set_bounds(self, kwargs_dict):
        try:
            self._min_value = kwargs_dict.pop(self.MINIMUM_KEY)
            self._max_value = kwargs_dict.pop(self.MAXIMUM_KEY)
        except KeyError as ex:
            s = f'Bounds are required. Was missing: {ex}'
            raise MissingAttributeKeywordError(s)

    def _check_bound_types(self, primitive_type_list):
        '''
        This checks that the bounds are sensible for the specific
        implementation of the bounded type.  For example, if we are
        creating a bounded integer, the bounds are also integers.

        The child implementations call this and provide the
        acceptable types as a list.
        '''
        d = {
            'minimum': self._min_value,
            'maximum': self._max_value
        }
        for k in d.keys():
            dtype = type(d[k])
            if not dtype in primitive_type_list:
                raise InvalidAttributeKeywordError(f'The value of the {k}'
                    f' bound ( {d[k]} ) specified does not match the expected'
                    f' type for this bounded attribute.')

    def to_dict(self):
        return {
            'attribute_type': self.typename,
            'value': self.value,
            self.MINIMUM_KEY: self._min_value,
            self.MAXIMUM_KEY: self._max_value,
        }

    def __repr__(self):
        return (f'{self.typename}: {self.value}'
            ' with bounds: [{self._min_val},{self._max_val}]')


class IntegerAttribute(BaseAttributeType):
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

    def _value_validator(self, val):
        if type(val) == int:
            self._value = val
        else:
            raise AttributeValueError(f'An integer attribute was expected,'
                ' but the value "{val}" could not be cast as an integer.')


class PositiveIntegerAttribute(BaseAttributeType):
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

    def _value_validator(self, val):
        if type(val) == int:
            if val > 0:
                self._value = val
            else:
                raise AttributeValueError(f'The value {val} was not a' 
                    ' positive integer.')
        else:
            raise AttributeValueError(f'A positive integer was expected,'
                ' but "{val}" is not an integer.')


class NonnegativeIntegerAttribute(BaseAttributeType):
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

    def _value_validator(self, val):
        if type(val) == int:
            if val >= 0:
                self._value = val
            else:
                raise AttributeValueError(
                    f'The value {val} is not a non-' 
                    'negative integer.')    
        else:
            raise AttributeValueError(
                f'A non-negative integer attribute was expected,'
                ' but "{val}" is not an integer.')


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

    def _value_validator(self, val):

        # here we also validate that the bounds are of
        # the same integer type
        self._check_bound_types([int])

        if type(val) == int:
            # the bounds were set by the constructor of the parent
            # `BoundedBaseAttribute` class
            if (val >= self._min_value) and (val <= self._max_value):
                self._value = val
            else:
                raise AttributeValueError(
                    f'The value {val} is not within the bounds' 
                    f' of [{self._min_value},{self._max_value}]')    
        else:
            raise AttributeValueError(
                f'A bounded integer attribute was expected,'
                f' but "{val}" is not an integer.')


class FloatAttribute(BaseAttributeType):
    '''
    General, unbounded float type
    ```
    {
        "attribute_type": "Float",
        "value": <float>
    }
    ```
    Note that positive/negative infinite values are acceptable
    provided they are specified using
    constants.POSITIVE_INF_MARKER
    constants.NEGATIVE_INF_MARKER
    '''
    typename = 'Float'

    def _value_validator(self, val):
        # ints can be floats, so we allow that.
        if (type(val) == float) or (type(val) == int):
            self._value = float(val)
        # infinite values can also be floats. We use our special marker values
        # to denote those.
        elif (val == POSITIVE_INF_MARKER) or (val == NEGATIVE_INF_MARKER):
            self._value = val
        else:
            raise AttributeValueError(
                f'A float attribute was expected, but'
                ' received "{val}"')


class PositiveFloatAttribute(BaseAttributeType):
    '''
    Positive (>0) float type
    ```
    {
        "attribute_type": "PositiveFloat",
        "value": <float>
    }
    ```
    Note that positive infinite values are acceptable
    provided they are specified using
    constants.POSITIVE_INF_MARKER
    '''
    typename = 'PositiveFloat'

    def _value_validator(self, val):
        
        if (type(val) == float) or (type(val) == int):
            if val > 0:
                self._value = float(val)
            else:
                raise AttributeValueError(f'Received a valid float ({val}),'
                    ' but it was not > 0.')
        elif val == POSITIVE_INF_MARKER:
            self._value = val
        else:
            raise AttributeValueError(
                f'A positive float attribute was expected, but'
                ' received "{val}"')


class NonnegativeFloatAttribute(BaseAttributeType):
    '''
    Non-negative (>=0) float type
    ```
    {
        "attribute_type": "NonNegativeFloat",
        "value": <float>
    }
    ```
    Note that positive infinite values are acceptable
    provided they are specified using
    constants.POSITIVE_INF_MARKER
    '''
    typename = 'NonNegativeFloat'

    def _value_validator(self, val):
        
        if (type(val) == float) or (type(val) == int):
            if val >= 0:
                self._value = float(val)
            else:
                raise AttributeValueError(f'Received a valid float ({val}),'
                    ' but it was not >= 0.')
        elif val == POSITIVE_INF_MARKER:
            self._value = val
        else:
            raise AttributeValueError(
                f'A float attribute was expected, but'
                ' received "{val}"')


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

    def _value_validator(self, val):

        # here we also validate that the bounds are of
        # the same integer type
        self._check_bound_types([int, float])

        if (type(val) == float) or (type(val) == int):
            if (val >= self._min_value) and (val <= self._max_value):
                self._value = val
            else:
                raise AttributeValueError(
                    f'The value {val} is not within the bounds' 
                    ' of [{self._min_value},{self._max_value}]') 
        else:
            raise AttributeValueError(
                f'A bounded float attribute was expected,'
                ' but "{val}" is not a float.')


class StringAttribute(BaseAttributeType):
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

    def _value_validator(self, val):
        try:
            val = normalize_identifier(val)
            self._value = val
        except StringIdentifierException as ex:
            raise AttributeValueError(str(ex))


class UnrestrictedStringAttribute(BaseAttributeType):
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

    def _value_validator(self, val):
        self._value = str(val)


class OptionStringAttribute(BaseAttributeType):
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
                        raise InvalidAttributeKeywordError('The options need to be'
                            f' strings. Failed on validating: {opt}')
                self._options = options
            else:
                raise InvalidAttributeKeywordError('Need to supply a list with'
                    f' the {self.OPTIONS_KEY} key.')
        except KeyError as ex:
            raise MissingAttributeKeywordError('Need a list of options given via'
                f' the {ex} key.')

    def _value_validator(self, val):

        if not val in self._options:
            raise AttributeValueError(f'The value "{val}" was not among'
                f' the valid options: {self._options}')
        self._value = val

    def to_dict(self):
        d = super().to_dict()
        d[self.OPTIONS_KEY] = self._options
        return d


class BooleanAttribute(BaseAttributeType):
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

    def _value_validator(self, val):
        '''
        Validates that the value can be interpreted
        as a boolean.  Either true/false or 1/0
        '''
        # Try various conventions for specifying bool. 
        # If we don't find anything that maches our expectation
        # then `final_val` will remain None, which will trigger
        # an exception
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
                self._value = True
            elif final_val in ['false', 0, False]:
                self._value = False
            else:
                raise Exception(f'Hit an edge case when trying to validate'
                    ' a boolean value.  Value was {val} and the "final value"'
                    ' was {final_val}')
        else:
            raise AttributeValueError(
                f'A boolean attribute was expected,'
                ' but "{val}" cannot be interpreted as such.') 


class BaseDataResourceAttribute(BaseAttributeType):
    '''
    Used to specify a reference to one or more Resource
    instances. This class should NOT be used directly. Instead,
    use one of the derived classes.

    Note that this is different than the actual file that holds the
    data. Rather, this is a way to specify that the input corresponds
    to a file.

    Note that "many" controls whether >1 are allowed. It's not an indicator
    for whether there are multiple Resources specified in the "value" key.

    Also note that the "value" of the derived classes is intended to be 
    one or more UUIDs and we validate that they are indeed UUIDs.
    However, we do NOT do any validation that contains API-specific logic.
    That is, this class is not responsible for determining whether an 
    actual Resource (the database model from the api package) has the
    correct type, is able to be used in an analysis, etc. These classes
    are only responsible for validating that the data structure was
    structured correctly.
    '''

    MANY_KEY = 'many'

    def __init__(self, value, **kwargs):

        try:
            v = kwargs.pop(self.MANY_KEY)
        except KeyError:
            raise MissingAttributeKeywordError('You must specify'
                ' a "many" key.')

        self._validate_many_key(v)
        super().__init__(value, **kwargs)
        
    def _validate_many_key(self, v):
        '''
        Checks that the value passed can be cast as a proper boolean 
        '''
        # use the BooleanAttribute to validate:
        b = BooleanAttribute(v)
        self._many = b.value

    def _value_validator(self, val):
        '''
        Validates that the value (or values)
        are proper UUIDs. 

        This is common for all the derived classes.
        '''
        # if a single UUID was passed, place it into a list:
        
        if (type(val) == str) or (type(val) == uuid.UUID):
            all_vals = [val,]
        elif type(val) == list:
            if self._many == False:
                raise AttributeValueError(f'The values ({val})'
                    ' are inconsistent with the many=False'
                    ' parameter.')
            all_vals = val
        else:
            raise AttributeValueError('Value needs to be either'
                ' a single UUID or a list of UUIDs.')

        try:
            all_vals = [str(x) for x in all_vals]
        except Exception as ex:
            logger.error('An unexpected exception occurred when trying'
                ' to validate a DataResource attribute.'
            )
            raise AttributeValueError('Unexpected validation problem when'
                ' validating a DataResource attribute.')

        for v in all_vals:
            try:
                # check that it is a UUID
                # Note that we can't explicitly check that a UUID
                # corresponds to a Resource database instance
                # as that creates a circular import dependency.
                uuid.UUID(v)
            except ValueError as ex:
                raise AttributeValueError(f'The passed value ({v}) was'
                    ' not a valid UUID.')
            except Exception as ex:
                raise AttributeValueError('Encountered an unknown exception'
                    ' when validating a DataResourceAttribute instance.'
                    ' Value was: {v}')
        self._value = val

    def to_dict(self):
        d = super().to_dict()
        d[self.MANY_KEY] = self._many
        return d


class DataResourceAttribute(BaseDataResourceAttribute):
    '''
    This class holds info that represents one or more resources
    of a fixed type.

    If the input can be one of multiple types, use one of the other
    classes.

    The serialized representation looks like:
    ```
    {
        "attribute_type": "DataResource",
        "value": <one or more Resource UUIDs>,
        "many": <bool>,
        "resource_type": <str>
    }
    ```  
    `resource_type` dictates the allowable type of resource
    (e.g. integer matrix only). It's value is matched against a controlled
    set of strings.  
    '''
    typename = 'DataResource'
    RESOURCE_TYPE_KEY = 'resource_type'
    REQUIRED_PARAMS = [BaseDataResourceAttribute.MANY_KEY, RESOURCE_TYPE_KEY]

    def __init__(self, value, **kwargs):
        try:
            self._validate_resource_type_key(kwargs.pop(self.RESOURCE_TYPE_KEY))
        except KeyError:
            raise MissingAttributeKeywordError('You must specify'
                f' a "{self.RESOURCE_TYPE_KEY}" key.')
        super().__init__(value, **kwargs)

    def _validate_resource_type_key(self, v):
        '''
        Checks that the value passed is one of the known
        resource types
        '''
        #TODO: add the validaton here- need all the available resource types
        self._resource_type = v

    def to_dict(self):
        d = super().to_dict()
        d[self.RESOURCE_TYPE_KEY] = self._resource_type
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


class VariableDataResourceAttribute(BaseDataResourceAttribute):
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

    # since we can accept multiple resource types, we
    # name the key appropriately (at the risk of typos 
    # for resource_type and resource_types).
    RESOURCE_TYPES_KEY = 'resource_types'
    REQUIRED_PARAMS = [BaseDataResourceAttribute.MANY_KEY, RESOURCE_TYPES_KEY]

    def __init__(self, value, **kwargs):
        try:
            self._validate_resource_types_key(
                kwargs.pop(self.RESOURCE_TYPES_KEY))
        except KeyError:
            raise MissingAttributeKeywordError('You must specify'
                f' a "{self.RESOURCE_TYPES_KEY}" key.')
        super().__init__(value, **kwargs)

    def _validate_resource_types_key(self, v):
        '''
        Checks that the value passed is a list
        consisting of only valid resource types
        '''
        if not type(v) is list:
            raise InvalidAttributeKeywordError(f'The {self.RESOURCE_TYPES_KEY}'
                ' keyword requires a list.')
        #TODO: add the validaton here- the various resource types
        self._resource_types = v

    def to_dict(self):
        d = super().to_dict()
        d[self.RESOURCE_TYPES_KEY] = self._resource_types
        return d