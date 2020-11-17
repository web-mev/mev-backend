import logging

logger = logging.getLogger(__name__)

from .observation import Observation
from .feature import Feature
from .observation_set import ObservationSet
from .feature_set import FeatureSet
from .attributes import IntegerAttribute, \
    PositiveIntegerAttribute, \
    NonnegativeIntegerAttribute, \
    FloatAttribute, \
    PositiveFloatAttribute, \
    NonnegativeFloatAttribute, \
    StringAttribute, \
    OptionStringAttribute, \
    BoundedIntegerAttribute, \
    BoundedFloatAttribute, \
    BooleanAttribute, \
    DataResourceAttribute, \
    create_attribute, \
    convert_dtype, \
    all_attribute_types, \
    numeric_attribute_typenames
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
    DataResourceInputSpec
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
    DataResourceOutputSpec
from .operation import Operation

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