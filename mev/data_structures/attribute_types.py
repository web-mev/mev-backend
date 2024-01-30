import logging

from constants import POSITIVE_INF_MARKER, NEGATIVE_INF_MARKER

from helpers import normalize_identifier
from exceptions import StringIdentifierException, \
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
            f' with bounds: [{self._min_value},{self._max_value}]')

    def __eq__(self, other):
        val_and_type_equal = super().__eq__(other)
        a = self._min_value == other._min_value
        b = self._max_value == other._max_value
        return all([val_and_type_equal, a, b])

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
                f' but the value "{val}" could not be cast as an integer.')


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
                f' but "{val}" is not an integer.')


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
                f' but "{val}" is not an integer.')


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
                'A float attribute was expected, but'
                f' received "{val}"')


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
                f' received "{val}"')


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
                'A float attribute was expected, but'
                f' received "{val}"')


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
                    f' of [{self._min_value},{self._max_value}]') 
        else:
            raise AttributeValueError(
                'A bounded float attribute was expected,'
                f' but "{val}" is not a float.')


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

    # Maximum length for a string. This is mainly
    # here as a guard against errors stemming from parsing
    # issues. For instance, parsing a CSV-format file as TSV
    # can result in entire lines being interpreted as a single,
    # ultra long string. While not a perfect solution, we can
    # at least catch issues like that (unless they are using a 
    # small file in which case it's impossible to differentiate
    # between a poorly parsed string and an intentionally long
    # string identifier)
    MAX_LENGTH = 100

    def _value_validator(self, val):
        try:
            val = normalize_identifier(val)
            if len(val) > self.MAX_LENGTH:
                raise AttributeValueError('The submitted attribute'
                    f' {val} was longer than we permit'
                    f' ({self.MAX_LENGTH} chars).')
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

    # Maximum length for a string. This is mainly
    # here as a guard against errors stemming from parsing
    # issues. For instance, parsing a CSV-format file as TSV
    # can result in entire lines being interpreted as a single,
    # ultra long string. While not a perfect solution, we can
    # at least catch issues like that (unless they are using a 
    # small file in which case it's impossible to differentiate
    # between a poorly parsed string and an intentionally long
    # string identifier)
    MAX_LENGTH = 1000

    def _value_validator(self, val):
        val = str(val)
        if len(val) > self.MAX_LENGTH:
            raise AttributeValueError('The submitted attribute'
                f' {val} was longer than we permit'
                f' ({self.MAX_LENGTH} chars).')
        self._value = val


class BaseOptionAttribute(BaseAttributeType):
    '''
    A String type that only admits values from a set of preset options
    (e.g. like a dropdown or multiselect)
    ```
    {
        "attribute_type": "OptionString",
        "value": <str>,
        "options": [<str>, <str>,...,<str>]
    }
    ```
    '''
    OPTIONS_KEY = 'options'
    MANY_KEY = 'many'
    REQUIRED_PARAMS = [OPTIONS_KEY, ]

    def __init__(self, value, **kwargs):
        self._set_options(kwargs)
        self._handle_many_key(kwargs)
        super().__init__(value, **kwargs)

    def _set_options(self, kwargs_dict):
        try:
            options = kwargs_dict.pop(self.OPTIONS_KEY)
            if type(options) == list:
                for opt in options:
                    if not type(opt) in self.BASE_TYPES:
                        raise InvalidAttributeKeywordError('The options must'
                            f' be one of ({", ".join(self.READABLE_TYPES)}).'
                            f' Failed on validating: {opt}')
                self._options = options
            else:
                raise InvalidAttributeKeywordError('Need to supply a list with'
                    f' the {self.OPTIONS_KEY} key.')
        except KeyError as ex:
            raise MissingAttributeKeywordError('Need a list of options given via'
                f' the {ex} key.')

    def _handle_many_key(self, kwargs):
        '''
        The 'many' key indicates whether we will accept multiple
        inputs (a subset of self._options with size > 1). The specification
        does not explicitly require the 'many' key, so it is False by default.
        However, if the key is given, we handle it here
        '''
        try:
            allow_many = kwargs.pop(self.MANY_KEY)
                    
            # use the BooleanAttribute to validate:
            b = BooleanAttribute(allow_many)
            self._many = b.value
        except KeyError as ex:
            self._many = False

    def _value_validator(self, val):
        '''
        Checks `val` against the available options.

        Note that if we accept many (self._many=True),
        then `val` can be a list, although that is not
        required (many ALLOWS it, but does not REQUIRE it)
        '''
        if type(val) is list:
            if self._many:
                _vals_to_check = val
            else:
                raise AttributeValueError(f'Multiple values were passed'
                    ' but only a single value is permitted unless explicitly'
                    ' permitted in the specification.')
        else: # not a list
            if self._many:
                raise AttributeValueError('When an option field permits many'
                    ' values, we require the values to be passed inside'
                    ' a list.')

            # we put inside a list to make the value checking easier below
            # for both single and multiple values
            _vals_to_check = [val,]
            
        for v in _vals_to_check:
            if not v in self._options:
                raise AttributeValueError(f'The value "{v}" was not among'
                    f' the valid options: {self._options}')
        self._value = val

    def to_dict(self):
        d = super().to_dict()
        d[self.OPTIONS_KEY] = self._options
        if self._many:
            d[self.MANY_KEY] = True
        return d


class OptionStringAttribute(BaseOptionAttribute):

    typename = 'OptionString'

    # this dictates the types that are permitted
    # in the finite set of options
    BASE_TYPES = [str,]

    # for a human-readable exception string
    READABLE_TYPES = ['string']


class IntegerOptionAttribute(BaseOptionAttribute):
    '''
    An integer type that only admits one from a set of preset values
    (e.g. like a dropdown)
    ```
    {
        "attribute_type": "IntegerOption",
        "value": <int>,
        "options": [<int>, <int>,...,<int/>]
    }
    ```
    '''
    typename = 'IntegerOption'

    # this dictates the types that are permitted
    # in the finite set of options
    BASE_TYPES = [int]

    # for a human-readable exception string
    READABLE_TYPES = ['integer']


class FloatOptionAttribute(BaseOptionAttribute):
    '''
    An float type that only admits one from a set of preset values
    (e.g. like a dropdown)
    ```
    {
        "attribute_type": "FloatOption",
        "value": <int>,
        "options": [<int/float>, <int/float>,...,<int/float>]
    }
    ```
    '''
    typename = 'FloatOption'

    # this dictates the types that are permitted
    # in the finite set of options
    BASE_TYPES = [float, int]

    # for a human-readable exception string
    READABLE_TYPES = ['float', 'integer']


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
                    f' a boolean value.  Value was {val} and the "final value"'
                    f' was {final_val}')
        else:
            raise AttributeValueError(
                'A boolean attribute was expected,'
                f' but "{val}" cannot be interpreted as such.')