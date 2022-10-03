import re

from data_structures.attribute_types import IntegerAttribute, \
    FloatAttribute, \
    StringAttribute, \
    UnrestrictedStringAttribute


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