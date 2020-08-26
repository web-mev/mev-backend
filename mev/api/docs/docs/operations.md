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
- name
- description of the analysis
- Inputs to the analysis.  These are the acceptable types and potentially some parameters.  For instance, a DESeq2 analysis should take an `IntegerMatrix`, two `ObservationSet` instances (defining the contrast groups), and a string "name" for the contrast. See below for a concrete example.
- Outputs of the analysis.  This would be similar to the inputs in that it describes the "types" of outputs.  Again, using the DESEq2 example, the outputs could be a "feature table" (`FT`, `FeatureTable`) giving the table of differentially expressed genes (e.g. fold-change, p-values) and a normalized expression matrix of type "expression matrix" (`EXP_MTX`).
- github repo/Docker info (commit hashes) so that the backend analysis code may be traced
- whether the `Operation` is a "local" one or requires use of the Cromwell engine. The front-end users don't need to know that, but internally MEV needs to know how to run the analysis.

Note that some of these will be specified by whoever creates the analysis. However, some information (like the UUID identifier, git hash, etc.) will be populated when the analysis is "ingested". It should not be the job of the analysis developer to maintain those pieces of information and we can create them on the fly during ingestion.

Therefore, an `Operation` has the following structure:
```
{
    "id": <UUID>,
    "name": <string>,
    "description": <string>,
    "inputs": Object<OperationInput>,
    "outputs": Object<OperationOutput>,
    "mode": <string>,
    "repository": <string url>,
    "git_hash": <string>
}
```
where:
- `mode`: identifies *how* the analysis is run. Will be one of an enum of strings (e.g. `local_docker`, `cromwell`)
- `repository`: identifies the github repo used to pull the data. For the ingestion, admins will give that url which will initiate a clone process. 
- `git_hash`: This is the commit hash which uniquely identifies the code state. This way the analysis code can be exactly traced back.

Both `inputs` and `outputs` address nested objects. That is, they are mappings of string identifiers to `OperationInput` or `OperationOutput` instances:

```
{
    'abc': <OperationInput/OperationOutput>,
    'def': <OperationInput/OperationOutput>
}
```

An `OperationInput` looks like:
```
{
    "description": <string>,
    "name": <string>,
    "required": <bool>,
    "spec": <InputSpec>
}
```
(and similarly for `OperationOutput`, which has fewer keys).

As an example of an `OperationInputs`, consider a p-value for thresholding:
```
{
    "description": "The filtering threshold for the p-value",
    "name": "P-value threshold:",
    "required": false,
    "spec": {
        "type": "BoundedFloat",
        "min": 0,
        "max": 1.0,
        "default": 0.05
    }
}
```
The `spec` key addresses a child class of `InputSpec` whose behavior is specific to each "type" (above, a `BoundedFloat`). There are only a limited number of those so defining a set of options for each is straightforward.


`ExecutedOperation`s should maintain the following data:

- The `Workspace` (which also gives access to the user/owner)
- a foreign-key to the `Operation` "type"
- unique identifier (UUID) for the execution
- a job identifier. We need the Cromwell job UUID to track the progress as we query the Cromwell server. For Docker-based jobs, we can set the tag on the container and then query its status (e.g. if it's still "up", then the job is still going)
- The inputs to the analysis (a JSON document)
- The outputs (another JSON document) once complete
- Job execution status (e.g. "running", "complete", "failed", etc.)
- Start time
- Completion time
- Any errors or warnings

--- 

### A concrete example

For this, consider a differential expression analysis (e.g. like DESeq2). In this simplified analysis, we will take a count matrix, a p-value (for filtering significance based on some hypothesis test), and an output file name. For outputs, we have a single file which has the results of the differential expression testing on each gene.  Since each row concerns a gene (and the columns give information about that gene), the output file is a "feature table" in our nomenclature.

Thus, the file which defines this analysis would look like:

```
{
    "name":"DESeq2 differential gene expression",
    "description": "Find genes which are differentially expressed and filter..."
    "inputs": {
        "count_matrix": {
            "description": "The count matrix of expressions",
            "name": "Count matrix:",
            "required": true,
            "spec": {
                "attribute_type": "DataResource",
                "resource_types": ["RNASEQ_COUNT_MTX", "I_MTX"],
                "many": false
            }
        },
        "p_val": {
            "description": "The filtering threshold for the p-value",
            "name": "P-value threshold:",
            "required": false,
            "spec": {
                "attribute_type": "BoundedFloat",
                "min": 0,
                "max": 1.0,
                "default": 0.05
            },
        }
        "output_filename": {
            "description": "The name of the contrast for your own reference.",
            "name": "Contrast name:",
            "required": false,
            "spec": {
                "attribute_type": "String",
                "default": "deseq2_results"
            }
        }
    },
    "outputs": {
        "dge_table": {
            "spec":{
                "attribute_type": "DataResource",
                "resource_type": "FT"
            } 
        }
    }
}
```
This specification will be placed into a file. In the repo, there will be a Dockerfile and possibly other files (e.g. scripts). Upon ingestion, MEV will read this inputs file, get the commit hash, assign a UUID, build the container, push the container, etc. 

As mentioned before, we note that the JSON above does not contain all of the required fields to create an `Operation` instance; it is missing `id`, `git_hash`, and`repository_url`. Note that when the API endpoint `/api/operations/` is requested, the returned object will match that above, but will also contain those required additional fields.

### Executing an Operation

The `Operation` objects above are typically used to populate the user interface such that the proper input fields can be displayed (e.g. a file chooser for an input that specifies it requires a `DataResource`). To actually initiate the `Operation`, thus creating an `ExecutedOperation`, the front-end (or API request) will need to POST a payload with the proper parameters/inputs. The backend will check those inputs against the specification.

As an example, a valid payload for the above would be:
```
{
    "operation_id": <UUID>,
    "workspace_id": <UUID>,
    "inputs": {
        "count_matrix": <UUID of Resource>
        "p_val": 0.01
    }
}
```
(note that the `"output_filename"` field was not required so we do not need it here)

The `operation_id` allows us to locate the `Operation` that we wish to run and the `workspace_id` allows us to associate the eventual `ExecutedOperation` with a `Workspace`. Finally, the `inputs` key is an object of key-value pairs. Depending on the "type" of the input, the values can be effectively arbitrary.

**Walking through the backend logic**
In the backend, we locate the proper `Operation` by its UUID. In our example, we see that this `Operation` expects two required inputs: `"count_matrix"` and `"p_val"`. Below, we walk though how these are validated.

For the `count_matrix` input, we see the `spec` field says it accepts `"DataResource"`s (files) with resource types of `["RNASEQ_COUNT_MTX", "I_MTX"]`. It also says `"many": false`, so we only will accept a single file. The payload example above provided a single UUID (so it is validated for `"many": false`). Then, we will take that UUID and query our database to see if it corresponds to a `Resource` instance that has a `resource_type` member that is either `"RNASEQ_COUNT_MTX"` or `"I_MTX"`. If that is indeed the case, then the `"count_matrix"` field is successfully validated.

For the `"p_val"` field, we receive a value of 0.01. The `spec` states that this input should be of type `BoundedFloat` with a min of 0.0 and a max of 1.0. The backend validates that 0.01 is indeed in the range [0.0,1.0].

Given that all the inputs successfully validate, we can move on to create an `ExecutedOperation` and actually run the analysis.
