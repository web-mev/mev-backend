<a id="observations"></a>
### Elements, Observations, and Features

We adopt the convention from statistical learning of referring to `Observation`s and `Feature`s of data.  Both of these data structures derive from `BaseElement`, which captures their common structure.  Specialization specific to each can be overridden in the child classes.  

In an experimental context, `Observation`s are analogous to samples.  That is, each `Observation` has one or more `Feature`s associated with it (e.g. gene expressions for 30,000 genes).  Collectively, we can think of `Observation`s and `Feature`s as comprising the rows and columns of a two-dimensional matrix.

We use `Observation`s and `Feature`s to hold metadata about data that we manipulating in MEV.  We can attach [attributes](attributes.md) to these to allow users to set experimental groups, or other information usedful for visualization or filtering.

These data structures have similar (if not exactly the same) behavior but we separate them for future compatability in case specialization of each class is needed.

::: api.data_structures.element.BaseElement
    :docstring:

::: api.data_structures.observation.Observation
    :docstring:

::: api.data_structures.feature.Feature
    :docstring: