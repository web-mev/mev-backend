### Attributes

`Attribute`s serve as "parameters" and are a way of providing validation and type-checking for values that are passed around within WebMEV.  The different types represent different simple entities within WebMEV. For example, we have simple wrappers around primitives like integers which enforce constraints on the underlying primitive type (e.g. for a probability, we can use a `BoundedFloatAttribute` set with bounds of [0,1]). Other types can represent and validate files ("data resources")

`Attribute`s are used to provide metadata (e.g. a phenotype of a sample given as a `StringAttribute`) or are used as parameters to analyses (e.g. a `BoundedFloatAttribute` for filtering p-values less than a particular value)


::: api.data_structures.attributes.BaseAttribute
    :docstring:

::: api.data_structures.attributes.BoundedBaseAttribute
    :docstring:

::: api.data_structures.attributes.IntegerAttribute
    :docstring:

::: api.data_structures.attributes.PositiveIntegerAttribute
    :docstring:

::: api.data_structures.attributes.NonnegativeIntegerAttribute
    :docstring:

::: api.data_structures.attributes.BoundedIntegerAttribute
    :docstring:

::: api.data_structures.attributes.FloatAttribute
    :docstring:

::: api.data_structures.attributes.PositiveFloatAttribute
    :docstring:

::: api.data_structures.attributes.NonnegativeFloatAttribute
    :docstring:

::: api.data_structures.attributes.BoundedFloatAttribute
    :docstring:

::: api.data_structures.attributes.StringAttribute
    :docstring:

::: api.data_structures.attributes.OptionStringAttribute
    :docstring:

::: api.data_structures.attributes.BooleanAttribute
    :docstring:

::: api.data_structures.attributes.DataResourceAttribute
    :docstring:

::: api.data_structures.attributes.OperationDataResourceAttribute
    :docstring:

::: api.data_structures.create_attribute
    :docstring:
