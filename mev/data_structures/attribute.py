import logging
from copy import deepcopy

from exceptions import NullAttributeError, \
    StringIdentifierException, \
    AttributeValueError, \
    InvalidAttributeKeywordError, \
    MissingAttributeKeywordError

from data_structures.feature import Feature
from data_structures.observation import Observation
from data_structures.observation_set import ObservationSet
from data_structures.feature_set import FeatureSet
from data_structures.attribute_types import IntegerAttribute, \
    PositiveIntegerAttribute, \
    NonnegativeIntegerAttribute, \
    BoundedIntegerAttribute, \
    FloatAttribute, \
    PositiveFloatAttribute, \
    NonnegativeFloatAttribute, \
    BoundedFloatAttribute, \
    StringAttribute, \
    UnrestrictedStringAttribute, \
    OptionStringAttribute, \
    BooleanAttribute, \
    DataResourceAttribute, \
    OperationDataResourceAttribute, \
    VariableDataResourceAttribute

logger = logging.getLogger(__name__)

attribute_types = [
    IntegerAttribute,
    PositiveIntegerAttribute,
    NonnegativeIntegerAttribute,
    BoundedIntegerAttribute,
    FloatAttribute,
    PositiveFloatAttribute,
    NonnegativeFloatAttribute,
    BoundedFloatAttribute,
    StringAttribute,
    UnrestrictedStringAttribute,
    OptionStringAttribute,
    BooleanAttribute,
    DataResourceAttribute,
    OperationDataResourceAttribute,
    VariableDataResourceAttribute,
    Feature,
    Observation,
    FeatureSet,
    ObservationSet
]
ATTRIBUTE_TYPE_MAPPING = {x.typename: x for x in attribute_types}


class Attribute(object):
    '''
    This class is best described as a factory which creates/holds
    a child class of `data_structures.attribute_types.BaseAttributeType`
    in its `value` field.

    The `value` (of type `BaseAttributeType`) is an instance of a 
    class that itself has a value and validation logic. For example, 
    we define a subclass of `BaseAttributeType` that only accepts 
    values within a certain bound and hence has member vars that 
    set the bounds (min, max) and validators that ensure values 
    are within those bounds.

    In the `Attribute` constructor, we pass a dict that contains
    an `attribute_type` key which defines the particular subclass
    of `BaseAttributeType` that we want. Other fields in that dict
    define the value and potentially other fields specific to the type.

    The dict passed to the constructor will have some JSON structure
    like
    ```
    {
        "attribute_type": <str>,
        "value": ...,
        ...other keys specific to the attribute...

    }
    ```
    For instance, a bounded float type would look like:
    ```
    {
        "attribute_type": "BoundedFloat",
        "value": 0.05,
        "min": 0.0,
        "max":1.0
    }
    ```
    Hence, the constructor of `Attribute` will know to create an
    instance of `BoundedFloatAttribute`. The other fields (value,
    min, max) are specific to that implementation class and will
    be passed to that class' constructor.

    Note that in addition to validating user-submitted values,
    other data structures (such as Input/OutputSpec) will use
    `Attribute` to validate the JSON-file that defines WebMeV
    Operation objects. In that case, those classes will leverage
    the logic here to verify that the JSON file was 
    correctly formatted, including validation of any default values.

    As an example, consider an analysis tool that has a default 
    p-value filter set to 0.05. Users are able to override this value,
    but the Operation states 0.05 as the default value. Hence, the
    Operation object looks, in part, like:
    ```
    {
        ...
        "inputs": {
            ...
            "pval_threshold": {
                "name": "P-value threshold",
                "description": ...
                ...
                "spec": {
                    "attribute_type": "BoundedFloat",
                    "default": 0.05,
                    "min": 0.0,
                    "max":1.0
                }
            }
            ...
        }
        ...
    }
    ```
    Thus, when we validate the Operation, we need to check that the 
    "default" value is acceptable for a bounded float on [0.0, 1.0].
    In that case, we pass 
    ```
    {
        "attribute_type": "BoundedFloat",
        "value": 0.05,
        "min": 0.0,
        "max":1.0
    }
    ```
    (note the "default" value was placed in the "value" key)
    and attempt to create a BoundedFloatAttribute with
    value of 0.05. If that works, then the specification for "pval_threshold"
    was acceptable. Otherwise, something was wrong. If no "default" is 
    provided, we pass `None` as the "value" (along with an `allow_null` kwarg
    to the constructor).
    '''

    def __init__(self, val, allow_null=False):
        '''
        As given in the class docstring, we expect a dict to be passed.
        The dict looks like:
        ```
        val  =  {
                    "attribute_type": "BoundedFloat",
                    "value": 0.05,
                    "min": 0.0,
                    "max":1.0
                }
        ```
        For cases where we are leveraging this class to validate an
        input or output specification (without a default), 
        we allow `None` to be passed for the `value` key, but ONLY
        if we get `allow_null=True`. That also covers the case where
        we do genuinely allow an attribute to be null/None.
        '''
        # The constructor expects a dict. Anything else
        # is rejected immedidately
        if not type(val) is dict:
            raise DataStructureValidationException('The constructor for an'
                ' Attribute expects a dictionary.')

        # to avoid any potential side effects, perform a copy on the dict
        attr_dict = deepcopy(val)

        # add on the `allow_null` so the actual implementing class
        # knows whether to accept a `None` value
        attr_dict['allow_null'] = allow_null

        # pop off the attribute type. The `attribute_type`
        # lets us know which subclass of BaseAttributeType we 
        # are instantiating. We don't need to pass this to that
        # class' constructor
        try:
            typename = attr_dict.pop('attribute_type')
        except KeyError:
            raise DataStructureValidationException('The "attribute_type"'
                ' key is required.') 

        # pop off the `value` key`. This leaves only "extra"
        # attribute-specific keys in `attr_dict`. Those are then
        # passed as kwargs to the constructor of the specific
        # attribute class
        try:
            attr_value = attr_dict.pop('value')
        except KeyError:
            raise DataStructureValidationException('The "value"'
                ' key is required.') 

        try:
            attribute_type_class = ATTRIBUTE_TYPE_MAPPING[typename]
        except KeyError:
            raise AttributeTypeError(f'Could not locate type: {typename}.')

        # Now that we have a class to instantiate, we pass what remains of
        # the `attr_dict`. Stash the instantiated class in the "private"
        # member _value.
        self._value = attribute_type_class(attr_value, **attr_dict)
   
    @property
    def value(self):
        '''
        Accessing the `value` attribute on this class returns
        the underlying instance of a BaseAttributeType subclass
        which is held in the `_value` member

        Note that we don't provide a setter. We want the instantiation
        of the `_value` to happen in this class' constructor.
        '''
        return self._value


