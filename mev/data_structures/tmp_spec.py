from data_structures.attribute import Attribute
from data_structures.compound_attribute import CompoundAttribute
from data_structures.attribute import attribute_types as simple_attribute_types
from data_structures.compound_attribute import attribute_types as compound_attribute_types

def get_type(t):
    t1 = [x.typename for x in simple_attribute_types]
    t2 = [x.typename for x in compound_attribute_types]
    if t in t1:
        return Attribute
    elif t in t2:
        return CompoundAttribute
    else:
        raise Exception('!!!')

