### Example workflow

To demonstrate how the various components of MEV come together, an graphical depiction of a typical workflow is shown below.  The steps will be discussed in detail and connected to the various entities of the MEV architecture.

![](tree.svg)

Associated with each `DataResource` (AKA a file, depicted as rectangles above) is an `ObservationSet`, a `FeatureSet`, neither, or both.  `ObservationSet` and `FeatureSet`s are essentially indexes on the columns/samples and the rows/genes as explained in [Resource metadata](resource_metadata.md).  

**Step-by-step**

- Denote the samples/columns of the original matrix (an instance of `ObservationSet`) as `all_observations`.  Similarly, denote all the rows/genes (an instance of `FeatureSet`) as `all_features`.

- The original count matrix is run through the "standard"/automatic analyses.  These are depicted using the gears and each are instances of `Operation`s.  An `Operation` is essentially a function-- it has some input(s) and produces some output(s).  Each of those `Operation` instances creates some output data/files.  The content/format of those is not important here.  Depending on the `Operation`, outputs could be flat files stored server-side (and served to the client) or simply data structures served to the client.

- One of those `Operation`s (PCA) allows you to create a "selection", which amounts to selecting a subset of all the samples.  This is shown at point "A" in the figure.  Through the UI, the user selects the desired samples (e.g. by clicking on points or dragging over areas of the PCA plot) and implicitly creates a client-side `ObservationSet`, which we will call `pca_based_filter`. This `pca_based_filter` is necessarily a subset of `all_observations`.  Note that the user does not know about the concept of `ObservationSet` instances.  Rather, they are simply selecting samples and choosing to group and label them according to some criteria (e.g. being clustered in a PCA plot).  Also note that the dotted line in the figure is meant to suggest that `pca_based_filter` was "inspired by" by the PCA `Operation`, but did not actually derive from it.  That is, while the visuals of the PCA plot were used to create the filter, the actual data of the PCA (the projected points) is not part of `pca_based_filter` (which is an `ObservationSet`).  Users can, however, name the `ObservationSet` so that they can be reminded of how these "selections" were made.   

- At point "B", we apply that `pca_based_filter` to filter the columns of the original count matrix (recall that the columns of that original file is `all_observations`).  Although the icon is not a "gear", the green circle denoting the application of the filter is still an `Operation` in the MEV context. Also, note that we can apply the `pca_based_filter` filter to *any* existing file that has an `ObservationSet`.  Obviously, it only provides a useful filter if there is a non-empty intersection of those sets; otherwise the filter produces an empty result.  That is technically a valid `Operation`, however.

    At this point, the only existing `DataResource`/file is the original count matrix which has an `ObservationSet` we called `all_observations`.   and we certainly have a non-empty intersection of the sets `pca_based_filter` and `all_observations`, so the filter is "useful".

    In accordance with our notion of an `Observation`, the filtering takes inputs (an `ObservationSet` and a `DataResource`) and produces output(s); here the output is another `DataResource` which we call `matrixA`.  In the backend, this creates both a physical file and a `Resource` in the database.  Recall that a `Resource` is just a way for MEV to track files, but is agnostic of the "behavior" of the files.
 
- We next run a differential expression analysis (DESeq2) on `matrixA`.  This produces a table of differential expression results.  Note that when we choose to run DESeq2, we will be given the option of choosing from all available count matrices.  In our case, that is either the original count matrix **or** the `matrixA`.  We choose `matrixA` in the diagram. 

- At point "C", we create a "row filter" by selecting the significantly differentially expressed genes from the DESeq2 results table.  Recall that in our nomenclature we call this a `FeatureSet`.  This `FeatureSet` (name it `dge_fs`) can then be applied to **any** of the existing files where it makes sense.  Again, by that I mean that it can be applied as a filter to any existing table that has a `FeatureSet`.  Currently those are:
    - original count matrix (where we called it `all_features`)
    - `matrixA` 
    - DESEq2 table

Since we have not yet applied any row filters, all three of those `DataResource`s/files have `FeatureSet`s equivalent to `all_features`.  The three files are shown flowing into node "D", but only one can be chosen (shown with solid line- `matrixA`)  

- At point "D", we apply `dge_fs` to `matrixA` in a filtering `Operation`.  This produces a new file which we call `matrixB`.  If you're keeping score, `matrixB` is basically the original table with both a row and column filter applied.

- We then run analyses on `matrixB`, such as a new PCA and a GSEA analysis.  

**Additional notes**

- This way of operation ends up producing multiple files that copy portions of the original matrix.  We could try and be slick and store those filter operations, but it's easier to just write new files.

- Allowing multiple `DataResource`s/files within a `Workspace` allows us to use multiple sources of data within an analysis.  In the older iterations MEV, all the analyses have to "flow" from a single original file.  This is more or less what we did in the figure above, but we are no longer constrained to operate in that way. One could imagine adding a VCF file to the `Workspace` which might allow one to perform an eQTL analysis, for example.