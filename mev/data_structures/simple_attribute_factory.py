from data_structures.factory import BaseAttributeFactory

# the "simple" attributes
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
    BooleanAttribute
from data_structures.list_attributes import StringListAttribute, \
    UnrestrictedStringListAttribute, \
    BoundedIntegerListAttribute, \
    BoundedFloatListAttribute
from data_structures.data_resource_attributes import DataResourceAttribute, \
    OperationDataResourceAttribute, \
    VariableDataResourceAttribute

simple_attribute_types = [
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
    StringListAttribute,
    UnrestrictedStringListAttribute,
    BoundedIntegerListAttribute,
    BoundedFloatListAttribute
]
simple_attribute_type_mapping = {x.typename: x for x in simple_attribute_types}

def SimpleAttributeFactory(val, allow_null=False):
    return BaseAttributeFactory(
        val, simple_attribute_type_mapping, allow_null=allow_null)