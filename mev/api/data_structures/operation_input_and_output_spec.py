import logging

from rest_framework.exceptions import ValidationError

from api.data_structures import Observation, Feature, ObservationSet, FeatureSet
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

    
class InputOutputSpec(object):
    '''
    Base class for objects that describe the inputs or outputs for an `Operation`.
    These are nested inside a `OperationInput` or `OperationOutput` object. 
    Behavior specific to each input type is described in the derived classes

    Note that these are "specifications" for the inputs/outputs, and NOT
    the actual value that a user might fill-in (or an analysis will create).  
    For example, an `Operation` may require a bounded float value (e.g. for a p-value). 
    In the JSON file specifying the inputs to this `Operation`, we have:
    ```
    "spec":{
        "attribute_type": "BoundedFloat",
        "min": <float>,
        "max": <float>,
        "default": <float>
    }
    ```
    When we are creating an `Operation` using this specification, we don't
    have a value-- we simply want to check that the specification is correct
    for the intended attribute_type. That is, given that we are stating it should be a
    BoundedFloat, we need to check that there are min and max values specified.
    We also need to ensure that the default value (if given) is sensible for those
    bounds.
    The child classes below perform those checks.

    When it comes to validating a user's input (so that they can run a specific
    `Operation`), we obviously have to check their input, but that is done in
    another class.
    '''
    def __init__(self, **kwargs):

        # to allow us to work with the serializers from the underlying
        # Attribute classes, we set the `value` attribute to None
        self.value = None
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

        # Note that below, we end up using the `check_keys`
        # method of the underlying "attribute" type. Therefore,
        # keys/params specific to the input/output specification
        # should be removed from the `kwargs_dict` at this point.
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

            # now reset the value to None:
            self.value = None
        except ValidationError as ex:
            logger.error('Error when inspecting an operation input/output.'
            ' Called with: {kwargs}.\nError was: {ex}'.format(
                kwargs=self.full_kwargs,
                ex=ex
            ))
            raise ex

    def to_representation(self, parent_class):
        d = parent_class.to_representation(self)
        # pop off the null value key-- input/output specs should not have
        # them. They were only added to aid with using the underlying
        # attribute classes
        d.pop('value')
        if self.default is not None:
            d['default'] = self.default
        return d

    def __eq__(self, other):
        return self.full_kwargs == other.full_kwargs

class IntegerInputOutputSpec(InputOutputSpec, IntegerAttribute):
    '''
    IntegerInputOutputSpec is an unbounded integer and can specify a default.
    e.g.
    ```
    {
        "attribute_type": "Integer",
        "default": <int>
    }
    ```
    '''
    def __init__(self, **kwargs):
        InputOutputSpec.__init__(self, **kwargs)
        kwargs = self.handle_common_kwargs(kwargs)
        if self.default is not None:
            self.check_default(IntegerAttribute, **kwargs)

    def to_representation(self):
        return InputOutputSpec.to_representation(self, IntegerAttribute)

class PositiveIntegerInputOutputSpec(InputOutputSpec, PositiveIntegerAttribute):
    '''
    PositiveIntegerInputOutputSpec is an integer > 0 and can specify a default.
    e.g.
    ```
    {
        "attribute_type": "PositiveInteger",
        "default": <int>
    }
    ```
    '''
    def __init__(self, **kwargs):
        InputOutputSpec.__init__(self, **kwargs)
        kwargs = self.handle_common_kwargs(kwargs)
        if self.default is not None:
            self.check_default(PositiveIntegerAttribute, **kwargs)

    def to_representation(self):
        return InputOutputSpec.to_representation(self, PositiveIntegerAttribute)

class NonnegativeIntegerInputOutputSpec(InputOutputSpec, NonnegativeIntegerAttribute):
    '''
    NonnegativeIntegerInputOutputSpec is an integer >= 0 and can specify a default.
    e.g.
    ```
    {
        "attribute_type": "NonnegativeInteger",
        "default": <int>
    }
    ```
    '''
    def __init__(self, **kwargs):
        InputOutputSpec.__init__(self, **kwargs)
        kwargs = self.handle_common_kwargs(kwargs)
        if self.default is not None:
            self.check_default(NonnegativeIntegerAttribute, **kwargs)

    def to_representation(self):
        return InputOutputSpec.to_representation(self, NonnegativeIntegerAttribute)

class BoundedIntegerInputOutputSpec(InputOutputSpec, BoundedIntegerAttribute):
    '''
    BoundedIntegerInputOutputSpec is an integer with defined bounds and 
    can specify a default. e.g.
    ```
    {
        "attribute_type": "BoundedInteger",
        "min": <int>,
        "max": <int>,
        "default": <int>
    }
    ```
    '''
    def __init__(self, **kwargs):
        InputOutputSpec.__init__(self, **kwargs)
        kwargs = self.handle_common_kwargs(kwargs)
        if self.default is not None:
            self.check_default(BoundedIntegerAttribute, **kwargs)
        self.set_bounds(kwargs)

        self.check_bound_types([int])

    def to_representation(self):
        return InputOutputSpec.to_representation(self, BoundedIntegerAttribute)

class FloatInputOutputSpec(InputOutputSpec, FloatAttribute):
    '''
    FloatInputOutputSpec is an unbounded float and can specify a default.
    e.g.
    ```
    {
        "attribute_type": "Float",
        "default": <float>
    }
    ```
    '''
    def __init__(self, **kwargs):
        InputOutputSpec.__init__(self, **kwargs)
        kwargs = self.handle_common_kwargs(kwargs)
        if self.default is not None:
            self.check_default(FloatAttribute, **kwargs)

    def to_representation(self):
        return InputOutputSpec.to_representation(self, FloatAttribute)

class PositiveFloatInputOutputSpec(InputOutputSpec, PositiveFloatAttribute):
    '''
    PositiveFloatInputOutputSpec is a float > 0 and can specify a default.
    e.g.
    ```
    {
        "attribute_type": "PositiveFloat",
        "default": <float>
    }
    ```
    '''
    def __init__(self, **kwargs):
        InputOutputSpec.__init__(self, **kwargs)
        kwargs = self.handle_common_kwargs(kwargs)
        if self.default is not None:
            self.check_default(PositiveFloatAttribute, **kwargs)

    def to_representation(self):
        return InputOutputSpec.to_representation(self, PositiveFloatAttribute)
        
class NonnegativeFloatInputOutputSpec(InputOutputSpec, NonnegativeFloatAttribute):
    '''
    NonnegativeFloatInputOutputSpec is a float >=0 and can specify a default.
    e.g.
    ```
    {
        "attribute_type": "NonnegativeFloat",
        "default": <float>
    }
    ```
    '''
    def __init__(self, **kwargs):
        InputOutputSpec.__init__(self, **kwargs)
        kwargs = self.handle_common_kwargs(kwargs)
        if self.default is not None:
            self.check_default(NonnegativeFloatAttribute, **kwargs)

    def to_representation(self):
        return InputOutputSpec.to_representation(self, NonnegativeFloatAttribute)
        
class BoundedFloatInputOutputSpec(InputOutputSpec, BoundedFloatAttribute):
    '''
    BoundedFloatInputOutputSpec is an integer with defined bounds and 
    can specify a default. e.g.
    ```
    {
        "attribute_type": "BoundedFloat",
        "min": <float>,
        "max": <float>,
        "default": <float>
    }
    ```
    '''
    def __init__(self, **kwargs):
        InputOutputSpec.__init__(self, **kwargs)
        kwargs = self.handle_common_kwargs(kwargs)
        if self.default is not None:
            self.check_default(BoundedFloatAttribute, **kwargs)

    def to_representation(self):
        return InputOutputSpec.to_representation(self, BoundedFloatAttribute)
        
class StringInputOutputSpec(InputOutputSpec, StringAttribute):
    '''
    StringInputOutputSpec is a string with some basic checking for
    characters that are "out of bounds".  See the string "normalizer"
    for the specific implementation that controls that behavior.
    ```
    {
        "attribute_type": "String",
        "default": <str>
    }
    ```
    '''
    def __init__(self, **kwargs):
        InputOutputSpec.__init__(self, **kwargs)
        kwargs = self.handle_common_kwargs(kwargs)
        if self.default is not None:
            self.check_default(StringAttribute, **kwargs)

    def to_representation(self):
        return InputOutputSpec.to_representation(self, StringAttribute)
        
class BooleanInputOutputSpec(InputOutputSpec, BooleanAttribute):
    '''
    Basic boolean.
    ```
    {
        "attribute_type": "Boolean",
        "default": <bool>
    }
    ```
    '''
    def __init__(self, **kwargs):
        InputOutputSpec.__init__(self, **kwargs)
        kwargs = self.handle_common_kwargs(kwargs)
        if self.default is not None:
            self.check_default(BooleanAttribute, **kwargs)

    def to_representation(self):
        return InputOutputSpec.to_representation(self, BooleanAttribute)
        
class DataResourceInputOutputSpec(InputOutputSpec, DataResourceAttribute):
    '''
    This InputOutputSpec is used for displaying/capturing
    inputs that are related to files.
    ```
    {
        "attribute_type": "DataResource",
        "many": <bool>,
        "resource_types": <list of valid resource types>
    }
    ```
    '''

    def __init__(self, **kwargs):
        InputOutputSpec.__init__(self, **kwargs)
        kwargs = self.validate_keyword_args(kwargs)
        kwargs = self.handle_common_kwargs(kwargs)

    def to_representation(self):
        i = InputOutputSpec.to_representation(self, DataResourceAttribute)
        return i


class ObservationInputOutputSpec(InputOutputSpec, Observation):
    '''
    Allows input/output fields that are based on our Observation
    objects.
    '''

    typename = "Observation"

    def __init__(self, **kwargs):
        InputOutputSpec.__init__(self, **kwargs)

    def to_representation(self):
        return {
            'attribute_type': self.typename
        }

class FeatureInputOutputSpec(InputOutputSpec, Feature):
    '''
    Allows input/output fields that are based on our Feature
    objects.
    '''

    typename = "Feature"

    def __init__(self, **kwargs):
        InputOutputSpec.__init__(self, **kwargs)

    def to_representation(self):
        return {
            'attribute_type': self.typename
        }

class ObservationSetInputOutputSpec(InputOutputSpec, ObservationSet):
    '''
    Allows input/output fields that are based on our ObservationSet
    objects.
    '''

    typename = "ObservationSet"

    def __init__(self, **kwargs):
        InputOutputSpec.__init__(self, **kwargs)

    def to_representation(self):
        return {
            'attribute_type': self.typename
        }


class FeatureSetInputOutputSpec(InputOutputSpec, FeatureSet):
    '''
    Allows input/output fields that are based on our FeatureSet
    objects.
    '''

    typename = "FeatureSet"

    def __init__(self, **kwargs):
        InputOutputSpec.__init__(self, **kwargs)
    
    def to_representation(self):
        return {
            'attribute_type': self.typename
        }