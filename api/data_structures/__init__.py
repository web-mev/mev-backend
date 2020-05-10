from .observation import Observation
from .observation_set import ObservationSet
from .attributes import IntegerAttribute, \
    PositiveIntegerAttribute, \
    NonnegativeIntegerAttribute, \
    FloatAttribute, \
    StringAttribute

numeric_attribute_types = [
    IntegerAttribute,
    PositiveIntegerAttribute,
    NonnegativeIntegerAttribute,
    FloatAttribute
]
numeric_attribute_typenames = [x.typename for x in numeric_attribute_types]

all_attribute_types = numeric_attribute_types + [StringAttribute,]
all_attribute_typenames = [x.typename for x in all_attribute_types]

attribute_mapping = dict(zip(all_attribute_typenames, all_attribute_types))

