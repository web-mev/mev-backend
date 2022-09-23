import re

from exceptions import AttributeTypeError

from data_structures.basic_attributes import IntegerAttribute, \
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
from data_structures.feature import Feature
from data_structures.observation import Observation
from data_structures.observation_set import ObservationSet
from data_structures.feature_set import FeatureSet


def convert_dtype(dtype_str, **kwargs):
    '''
    Takes a pandas/numpy dtype (string) and returns an 
    ppropriate attribute "type" string.  
    For instance, if "int64", return Integer.
    '''

    if re.match('int\d{0,2}', dtype_str):
        return IntegerAttribute.typename
    elif re.match('float\d{0,2}', dtype_str):
        return FloatAttribute.typename
    else:
        if 'allow_unrestricted_strings' in kwargs:
            return UnrestrictedStringAttribute.typename
        return StringAttribute.typename


def get_attribute_implementation(attribute_key):
    '''
    Given a 'key' (the typename attribute), return
    the class that implements the desired type

    For instance, given "PositiveInteger", return the
    PositiveIntegerAttribute class.

    Note that this returns the class itself, not an
    instance of said class
    '''
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
    mapping = {x.typename: x for x in attribute_types}
    try:
        return mapping[attribute_key]
    except KeyError as ex:
        raise AttributeTypeError(f'Could not locate type: {attribute_key}.')
