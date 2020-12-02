import logging

from rest_framework.exceptions import ValidationError

logger = logging.getLogger(__name__)

from .attributes import IntegerAttribute, \
    PositiveIntegerAttribute, \
    NonnegativeIntegerAttribute, \
    FloatAttribute, \
    PositiveFloatAttribute, \
    NonnegativeFloatAttribute, \
    StringAttribute, \
    UnrestrictedStringAttribute, \
    OptionStringAttribute, \
    BoundedIntegerAttribute, \
    BoundedFloatAttribute, \
    BooleanAttribute, \
    DataResourceAttribute, \
    convert_dtype
from .list_attributes import StringListAttribute, \
    UnrestrictedStringListAttribute

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
other_attribute_types = [
    StringAttribute,
    UnrestrictedStringAttribute,
    BooleanAttribute, 
    DataResourceAttribute, 
    OptionStringAttribute,
    StringListAttribute,
    UnrestrictedStringListAttribute
]
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

from .observation import Observation
from .feature import Feature
from .observation_set import ObservationSet
from .feature_set import FeatureSet
from .operation_input import OperationInput
from .operation_input_spec import IntegerInputSpec, \
    PositiveIntegerInputSpec, \
    NonnegativeIntegerInputSpec, \
    BoundedIntegerInputSpec, \
    FloatInputSpec, \
    PositiveFloatInputSpec, \
    NonnegativeFloatInputSpec, \
    BoundedFloatInputSpec, \
    StringInputSpec, \
    OptionStringInputSpec, \
    BooleanInputSpec, \
    ObservationInputSpec, \
    ObservationSetInputSpec, \
    FeatureInputSpec, \
    FeatureSetInputSpec, \
    DataResourceInputSpec, \
    StringListInputSpec, \
    UnrestrictedStringListInputSpec
from .operation_output import OperationOutput
from .operation_output_spec import IntegerOutputSpec, \
    PositiveIntegerOutputSpec, \
    NonnegativeIntegerOutputSpec, \
    BoundedIntegerOutputSpec, \
    FloatOutputSpec, \
    PositiveFloatOutputSpec, \
    NonnegativeFloatOutputSpec, \
    BoundedFloatOutputSpec, \
    StringOutputSpec, \
    OptionStringOutputSpec, \
    BooleanOutputSpec, \
    ObservationOutputSpec, \
    ObservationSetOutputSpec, \
    FeatureOutputSpec, \
    FeatureSetOutputSpec, \
    DataResourceOutputSpec, \
    StringListOutputSpec, \
    UnrestrictedStringListOutputSpec
from .operation import Operation
from .dag_components import DagNode, SimpleDag

def merge_element_set(element_set_list):
    '''
    Takes a list of BaseElementSet instances (ObservationSet or FeatureSet)
    and performs a union on the elements.

    Only performs the union using the basic behavior of a BaseElementSet. If 
    you require some behavior specific to say, an ObservationSet, then do NOT
    use this function.
    '''

    # check that all elements of the list are the same type:
    unique_types = set([type(x) for x in element_set_list])
    if len(unique_types) > 1:
        logger.info('Failed when attempting to'
            ' merge types: {s}'.format(s=', '.join(unique_types)))
        raise Exception('Attempting to merge more than one type.')
    elif len(unique_types) == 0:
        logger.info('Empty type list. Returning None')
        return None
        
    # check that the type is a subclass of BaseElementSet
    from .element_set import BaseElementSet
    typeclass = list(unique_types)[0]
    if not issubclass(typeclass, BaseElementSet):
        logger.info('Failed when attempting to merge type: {t}'.format(t=typeclass))
        raise Exception('Cannot merge type: {t}'.format(t=typeclass))

    # ok, at this point we have a list of one type which is a subclass
    # of the BaseElementSet
    elements = set()
    for x in element_set_list:
        new_elements = x.elements
        elements = elements.union(new_elements)
    
    # now create an "element set" of the proper type:
    s = typeclass(elements)
    return s