### Operations and ExecutedOperations

An `Operation` is *any* manipulation of some data that produces some output; it defines the type of analysis that is run, its inputs and outputs, and other relevant information. An `Operation` can be as simple as selecting a subset of the columns/rows of a matrix or running a large-scale processing job that spans many machines and significant time. 

An `ExecutedOperation` represents an actual execution of an `Operation`.  While the `Operation` identifies the process used, the `ExecutedOperation` contains information about the actual execution, such as the job status, the exact inputs and outputs, the runtime, and other relevant information. Clearly, the `ExecutedOperation` maintains a foreign-key relation to the `Operation`.

The various `ExecutedOperation`s performed in MEV will all create some output so that there will be no ambiguity regarding how data was manipulated through the course of an analysis workflow. Essentially, we do not perform *in-place* operations on data.  For example, if a user chooses a subset of samples/columns in their expression matrix, we create a new `DataResource` (and corresponding `Resource` database record).  While this has the potential to create multiple files with similar data, this makes auditing a workflow history much simpler.  Typically, the size of files where users are interacting with the data are relatively small (on the order of MB) so excessive storage is not a major concern.

Note that client-side manipulations of the data, such as filtering out samples are distinct from this concept of an `Operation`/`ExecutedOperation`.  That is, users can select various filters on their data to change the visualizations without executing any `Operation`s.  *However*, once they choose to use the subset data for use in an analysis, they will be required to implicitly execute an `Operation` on the backend.  As a concrete example, consider analyzing a large cohort of expression data from TCGA.  A user initially imports the expression matrix and perhaps uses PCA or some other clustering method in an exploratory analysis. Each of those initial analyses were `ExecutedOperation`s.  Based on those initial visualizations, the user may select a subset of those samples to investigate for potential subtypes; note that those client-side sample selections have not triggered any actual analyses.  However, once they choose to run those samples through a differential expression analysis, we require that they perform filter/subset `Operation`.  


As new `DataResource`s are created, the metadata tracks which `ExecutedOperation` created them, addressed by the UUID assigned to each `ExecutedOperation`.  By tracing the foreign-key relation, we can determine the exact `Operation` that was run so that the steps of the analysis are transparent and reproducible.

`Operation`s can be lightweight jobs such as a basic filter or a simple R script, or involve complex, multi-step pipelines orchestrated using the CNAP-style workflows involving WDL and Cromwell.  Depending on the computational resources needed, the `Operation` can be run locally or remotely.  As jobs complete, their outputs will populate in the user's workspace and further analysis can be performed.

All jobs, whether local or remote, will be placed in a queue and executed ascynchronously. Progress/status of remote jobs can be monitored by querying the Cromwell server.

Also note that ALL `Operation`s (even basic table filtering) are executed in Docker containers so that the software and environments can be carefully tracked and controlled.  This ensures a consistent "plugin" style architecture so that new `Operation`s can be integrated consistently.

`Operation`s should maintain the following data:

- unique identifier (UUID)
- a simplier "version" identifier (e.g. "v1").  This allows us to change analyses over time but let users recreate earlier analyses so that their processing is consistent/reproducible.
- name
- description of the analysis
- Inputs to the analysis.  These are the acceptable types and potentially some parameters.  For instance, a DESeq2 analysis should take an `IntegerMatrix`, two `ObservationSet` instances (defining the contrast groups), and a string "name" for the contrast.
- Outputs of the analysis.  This would be the "types" of outputs.  Again, using the DESEq2 example, the outputs could be a `TableResource` giving the table of differentially expressed genes (e.g. fold-change, p-values) and a normalized expression matrix of type `Matrix`.
- github repo/Docker info (commit hashes) so that the backend analysis code may be traced
- whether the `Operation` is a "local" one or requires use of the Cromwell engine.

`ExecutedOperation`s should maintain the following data:

- The `Workspace` (which also gives access to the user/owner)
- a foreign-key to the `Operation` "type"
- unique identifier (UUID) for the execution
- a job identifier if the analysis is run remotely (on Cromwell).  We need the Cromwell job UUID to track the progress as we query the Cromwell server.
- The inputs to the analysis (e.g. the UUIDs of the `Resource`s that were input)
- The outputs (more UUIDs of the `Resource`s created) once complete
- Job execution status (e.g. "running", "complete", "failed", etc.)
- Start time
- Completion time
- Any errors or warnings