### Attributes

`Attribute`s serve as "parameters" and are a way of providing validation and type-checking for values that are passed around within WebMEV.  The different types represent different simple entities within WebMEV. For example, we have simple wrappers around primitives like integers which enforce constraints on the underlying primitive type (e.g. for a probability, we can use a `BoundedFloatAttribute` set with bounds of [0,1]). Other types can represent and validate files ("data resources")

`Attribute`s are used to provide metadata (e.g. a phenotype of a sample given as a `StringAttribute`) or are used as parameters to analyses (e.g. a `BoundedFloatAttribute` for filtering p-values less than a particular value)


::: data_structures.base_attribute.BaseAttributeType
    :docstring:

::: data_structures.attribute_types.BoundedBaseAttribute
    :docstring:

::: data_structures.attribute_types.IntegerAttribute
    :docstring:

::: data_structures.attribute_types.PositiveIntegerAttribute
    :docstring:

::: data_structures.attribute_types.NonnegativeIntegerAttribute
    :docstring:

::: data_structures.attribute_types.BoundedIntegerAttribute
    :docstring:

::: data_structures.attribute_types.FloatAttribute
    :docstring:

::: data_structures.attribute_types.PositiveFloatAttribute
    :docstring:

::: data_structures.attribute_types.NonnegativeFloatAttribute
    :docstring:

::: data_structures.attribute_types.BoundedFloatAttribute
    :docstring:

::: data_structures.attribute_types.StringAttribute
    :docstring:

::: data_structures.attribute_types.OptionStringAttribute
    :docstring:

::: data_structures.attribute_types.BooleanAttribute
    :docstring:

::: data_structures.data_resource_attributes.DataResourceAttribute
    :docstring:

::: data_structures.data_resource_attributes.OperationDataResourceAttribute
    :docstring:
