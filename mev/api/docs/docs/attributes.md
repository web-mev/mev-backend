### Attributes

`Attribute`s could also be thought of as "parameters" and are a way of providing validated key-value pairs.  The different types enforce various constraints on the underlying primitive type (e.g. a float bounded between [0,1] can represent a probability).

Mainly, `Attribute`s are a way to add information to [`Observation` or `Feature`](elements.md) instances.  For example, one could specify the phenotype or experimental group of an `Observation` via a `StringAttribute`.

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

::: api.data_structures.attributes.create_attribute
    :docstring:
