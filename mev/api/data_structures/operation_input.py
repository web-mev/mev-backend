import logging

from rest_framework.exceptions import ValidationError

from api.data_structures.attributes import IntegerAttribute, \
    PositiveIntegerAttribute, \
    NonnegativeIntegerAttribute, \
    BoundedIntegerAttribute, \
    FloatAttribute, \
    PositiveFloatAttribute, \
    NonnegativeFloatAttribute, \
    BoundedFloatAttribute, \
    StringAttribute, \
    BooleanAttribute, \
    DataResourceAttribute

logger = logging.getLogger(__name__)

class OperationInput(object):
    '''
    This class defines a general data structure that holds information about
    inputs to an analysis (`Operation`)
    '''

    def __init__(self, description, name, spec, required=False):

        # a descriptive field to help users
        self.description = description

        # the label of the field in the UI
        self.name = name

        # whether the input field is actually required
        self.required = required

        # a nested object which describes the input itself (e.g. 
        # a number, a string, a file). Of type `InputSpec`
        self.spec = spec


class InputSpec(object):
    '''
    Base class for objects that describe the inputs for an `Operation`.
    These are nested inside a `OperationInput` object. Behavior specific
    to each input type is described in the derived classes

    Note that these are "specifications" for the inputs, and do NOT
    want the actual value that a user might fill-in.  For example, an `Operation`
    may be require a bounded float value (e.g. for a p-value). In the JSON file
    specifying the inputs to this `Operation`, we have:
    ```
        
    "input_spec":{
        "type": "BoundedFloat",
        "min": <float>,
        "max": <float>,
        "default": <float>
    }
    ```
    When we are creating an `Operation` using this specification, we don't
    have a value-- we simply want to check that the specification is correct
    for the intended type. That is, given that we are stating it should be a
    BoundedFloat, we need to check that there are min and max values specified.
    We also need to ensure that the default value (if given) is sensible for those
    bounds.
    The child classes below perform those checks.

    When it comes to validating a user's input (so that they can run a specific
    `Operation`), we obviously have to check their input, but that is done in
    another class.
    '''
    def __init__(self, **kwargs):
        self.full_kwargs = kwargs.copy()

    def handle_common_kwargs(self, kwargs_dict):
        '''
        This method handles various keyword args passed
        to the constructor of the subclasses.
        '''
        try:
            self.default = kwargs_dict.pop('default')
        except KeyError as ex:
            self.default = None

        params = list(kwargs_dict.keys())
        self.check_keys(params)
        return kwargs_dict

    def check_default(self, implementation_class, **kwargs):
        '''
        Checks that the default value (if given) is sensible for the particular
        input spec type (e.g. if an "Integer" type gets a default of 3.2, then 
        that is an error).

        The `implementation_class` is the class that will actually validate 
        the default for that class. For instance, a `BoundedInteger` will use
        that class' constructor to check that the default is valid and satisfies
        the constraints of the `BoundedInteger` class
        '''
        try:
            implementation_class.__init__(self, self.default, **kwargs)
        except ValidationError as ex:
            logger.error('Error when inspecting an operation input.'
            ' Called with: {kwargs}.\nError was: {ex}'.format(
                kwargs=self.full_kwargs,
                ex=ex
            ))
            raise ex


class IntegerInputSpec(InputSpec, IntegerAttribute):
    '''
    IntegerInputSpec is an unbounded integer and can specify a default.
    e.g.
    ```
    {
        "type": "Integer",
        "default": <int>
    }
    ```
    '''
    def __init__(self, **kwargs):
        InputSpec.__init__(self, **kwargs)
        kwargs = self.handle_common_kwargs(kwargs)
        if self.default is not None:
            self.check_default(IntegerAttribute, **kwargs)

class PositiveIntegerInputSpec(InputSpec, PositiveIntegerAttribute):
    '''
    PositiveIntegerInputSpec is an integer > 0 and can specify a default.
    e.g.
    ```
    {
        "type": "PositiveInteger",
        "default": <int>
    }
    ```
    '''
    def __init__(self, **kwargs):
        InputSpec.__init__(self, **kwargs)
        kwargs = self.handle_common_kwargs(kwargs)
        if self.default is not None:
            self.check_default(PositiveIntegerAttribute, **kwargs)


class NonnegativeIntegerInputSpec(InputSpec, NonnegativeIntegerAttribute):
    '''
    NonnegativeIntegerInputSpec is an integer >= 0 and can specify a default.
    e.g.
    ```
    {
        "type": "NonnegativeInteger",
        "default": <int>
    }
    ```
    '''
    def __init__(self, **kwargs):
        InputSpec.__init__(self, **kwargs)
        kwargs = self.handle_common_kwargs(kwargs)
        if self.default is not None:
            self.check_default(NonnegativeIntegerAttribute, **kwargs)


class BoundedIntegerInputSpec(InputSpec, BoundedIntegerAttribute):
    '''
    BoundedIntegerInputSpec is an integer with defined bounds and 
    can specify a default. e.g.
    ```
    {
        "type": "BoundedInteger",
        "min": <int>,
        "max": <int>,
        "default": <int>
    }
    ```
    '''
    def __init__(self, **kwargs):
        InputSpec.__init__(self, **kwargs)
        kwargs = self.handle_common_kwargs(kwargs)
        if self.default is not None:
            self.check_default(BoundedIntegerAttribute, **kwargs)
        self.set_bounds(kwargs)
        self.check_bound_types([int])


class FloatInputSpec(InputSpec, FloatAttribute):
    '''
    FloatInputSpec is an unbounded float and can specify a default.
    e.g.
    ```
    {
        "type": "Float",
        "default": <float>
    }
    ```
    '''
    def __init__(self, **kwargs):
        InputSpec.__init__(self, **kwargs)
        kwargs = self.handle_common_kwargs(kwargs)
        if self.default is not None:
            self.check_default(FloatAttribute, **kwargs)


class PositiveFloatInputSpec(InputSpec, PositiveFloatAttribute):
    '''
    PositiveFloatInputSpec is a float > 0 and can specify a default.
    e.g.
    ```
    {
        "type": "PositiveFloat",
        "default": <float>
    }
    ```
    '''
    def __init__(self, **kwargs):
        InputSpec.__init__(self, **kwargs)
        kwargs = self.handle_common_kwargs(kwargs)
        if self.default is not None:
            self.check_default(PositiveFloatAttribute, **kwargs)


class NonnegativeFloatInputSpec(InputSpec, NonnegativeFloatAttribute):
    '''
    NonnegativeFloatInputSpec is a float >=0 and can specify a default.
    e.g.
    ```
    {
        "type": "NonnegativeFloat",
        "default": <float>
    }
    ```
    '''
    def __init__(self, **kwargs):
        InputSpec.__init__(self, **kwargs)
        kwargs = self.handle_common_kwargs(kwargs)
        if self.default is not None:
            self.check_default(NonnegativeFloatAttribute, **kwargs)


class BoundedFloatInputSpec(InputSpec, BoundedFloatAttribute):
    '''
    BoundedFloatInputSpec is an integer with defined bounds and 
    can specify a default. e.g.
    ```
    {
        "type": "BoundedFloat",
        "min": <float>,
        "max": <float>,
        "default": <float>
    }
    ```
    '''
    def __init__(self, **kwargs):
        InputSpec.__init__(self, **kwargs)
        kwargs = self.handle_common_kwargs(kwargs)
        if self.default is not None:
            self.check_default(BoundedFloatAttribute, **kwargs)


class StringInputSpec(InputSpec, StringAttribute):
    '''
    StringInputSpec is a string with some basic checking for
    characters that are "out of bounds".  See the string "normalizer"
    for the specific implementation that controls that behavior.
    ```
    {
        "type": "String",
        "default": <str>
    }
    ```
    '''
    def __init__(self, **kwargs):
        InputSpec.__init__(self, **kwargs)
        kwargs = self.handle_common_kwargs(kwargs)
        if self.default is not None:
            self.check_default(StringAttribute, **kwargs)


class BooleanInputSpec(InputSpec, BooleanAttribute):
    '''
    Basic boolean.
    ```
    {
        "type": "Boolean",
        "default": <bool>
    }
    ```
    '''
    def __init__(self, **kwargs):
        InputSpec.__init__(self, **kwargs)
        kwargs = self.handle_common_kwargs(kwargs)
        if self.default is not None:
            self.check_default(BooleanAttribute, **kwargs)


class DataResourceInputSpec(InputSpec, DataResourceAttribute):
    '''
    This InputSpec is used for displaying/capturing
    inputs that are related to files.

    Unlike the other InputSpec children classes above, there is
    no "primitive" data structure that this sits on top of.

    ```
    {
        "type": "DataResource",
        "many": <bool>,
        "resource_types": <list of valid resource types>
    }
    ```
    '''

    def __init__(self, **kwargs):
        InputSpec.__init__(self, **kwargs)
        kwargs = self.handle_common_kwargs(kwargs)
        kwargs = self.validate_keyword_args(kwargs)

    #TODO when deserializing the instance, validation will check that
    # the resource types of the UUIDs are valid.