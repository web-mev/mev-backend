<a id="observations"></a>
### Elements, Observations, and Features

We adopt the convention from statistical learning of referring to `Observation`s and `Feature`s of data.  Both of these data structures derive from the `BaseElement` class, which captures their common structure and behavior.  Specialization for each can be overridden in the child classes.  

In the context of a biological experimental, `Observation`s are synonymous with samples.  Further, each `Observation` can have `Feature`s associated with it (e.g. gene expressions for 30,000 genes).  One can think of `Observation`s and `Feature`s as comprising the columns and rows of a two-dimensional matrix. Note that in our convention, due to the typical format of expression matrices, we take each column to represent an `Observation` and each row to represent a `Feature`. 

We use `Observation`s and `Feature`s to hold metadata (as key-value pairs) about data that we manipulating in WebMEV. For instance, given a typical gene expression matrix we have information about only the *names* of the `Observation`s/samples and `Feature`s/genes. We can then specify [attributes](attributes.md) to annotate the `Observation`s and `Feature`s, allowing users to define experimental groups, or specify other information useful for visualization or filtering.

These data structures have similar (if not exactly the same) behavior but we separate them for future compatability in case specialization of each class is needed.

::: api.data_structures.element.BaseElement
    :docstring:

::: api.data_structures.observation.Observation
    :docstring:

::: api.data_structures.feature.Feature
    :docstring: