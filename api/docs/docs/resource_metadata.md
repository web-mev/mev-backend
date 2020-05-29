### Resource metadata

Metadata can be associated with type of `DataResource`.  

Note that a `DataResource` is related, but distinct from a `Resource`.  The latter is for tracking the various file-based resources in the database; it knows about the file location, size, and the type of the resource (as a string field).  The former is a base class from which the many specialized "types" of resources derive.  For instance, an `IntegerMatrix` derives from a `DataResource`.  Instead of being a database record, a `DataResource` captures the expected format and behavior of the resource.  For instance, the children classes of `DataResource` contain validators and parsers.

Thus, associated with each `DataResource` is some metadata.  The specification may expand to incorporate additional fields, but at minimum, it should contain:

- An `ObservationSet`.  For a FastQ file representing a single sample (most common case), the `ObservationSet` would have a single item (of type `Observation`) containing information about that particular sample.  For a count matrix of size (p, N), the `ObservationSet` would have N items (again, of type `Observation`) giving information about the samples in the columns.

- A `FeatureSet`.  This is a collection of covariates corresponding to a single `Observation`.  A `Feature` is something that is measured (e.g. read counts for a gene). For a count matrix of size (p, N), the `FeatureSet` would have p items (of type `Feature`) and correspond to the p genes measured for a single sample. For a sequence-based file like a FastQ, this would simply be null; perhaps there are alternative intepretations of this concept, but the point is that the field *can* be null.  A table of differentially expressed genes would have a `FeatureSet`, but not an
`ObservationSet`; in this case the `Feature`s are the genes and we are given information like log-fold change and p-value.

- A parent operation.  As an analysis workflow can be represented as a directed, acyclic graph (DAG), we would like to track the flow of data and operations on the data.  Tracking the "parent" of a `DataResource` allows us to determine which operation generated the data and hence reconstruct the full DAG.  The original input files would have a null parent.

We maintain a "master copy" of the metadata on the server side as a flat file for reference.  We do not want to have to repeatedly open/parse a large text file to determine the rows/features and columns/observations.  We imagine that for performance reasons, client-applications may choose to cache this metadata so that desired sets of rows or columns can be selected on the client side without involving a request to the server.

Requests to subset/filter a `DataResource` would provide `ObservationSet`s or `FeatureSet`s which are compared against the respective `ObservationSet`s or `FeatureSet`s of the `DataResource`.