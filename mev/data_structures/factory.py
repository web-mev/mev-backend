import logging
from copy import deepcopy

from exceptions import AttributeTypeError, \
    DataStructureValidationException

logger = logging.getLogger(__name__)


def BaseAttributeFactory(val, 
    type_mapping, allow_null=False, ignore_extra_keys=False):
    '''
    This function is a factory which creates/returns
    a child class of `data_structures.attribute_types.BaseAttributeType`
    i

    For the first arg `val`, we pass a dict that contains
    an `attribute_type` key which defines the particular subclass
    of `BaseAttributeType` that we want. Other fields in that dict
    define the value and potentially other fields specific to the type.

    `val` will have some JSON structure
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
    Hence, we know to create and return an
    instance of `BoundedFloatAttribute`. The other fields (value,
    min, max) are specific to that implementation class and will
    be passed to that class' constructor.

    Note that in addition to validating user-submitted values,
    other data structures (such as Input/OutputSpec) will use
    this to validate the JSON-file that defines WebMeV
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
    to this function).
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

    # In the case where we want to allow extra keys to be
    # passed to the constructor (which are ignored:
    attr_dict['ignore_extra_keys'] = ignore_extra_keys

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
        attribute_type_class = type_mapping[typename]
    except KeyError:
        raise AttributeTypeError(f'Could not locate type: {typename}.')

    # Now that we have a class to instantiate, we pass what remains of
    # the `attr_dict`. Stash the instantiated class in the "private"
    # member _value.
    return attribute_type_class(attr_value, **attr_dict)