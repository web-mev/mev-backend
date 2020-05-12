<a id="observations"></a>
### Observations

We adopt the convention from statistical learning of referring to `Observation`s.  In an experimental context, `Observation`s are analogous to samples.  That is, each `Observation` has one or more `Feature`s associated with it (e.g. gene expressions for 30,000 genes).

We use `Observation`s to hold metadata about data that we manipulating in MEV.  We can attach [attributes](attributes.md) to these to allow users to set experimental groups, or other information usedful for visualization or filtering.

::: api.data_structures.observation.Observation
    :docstring:
