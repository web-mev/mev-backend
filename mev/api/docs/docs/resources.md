### Resources

`Resource`s represent data in some file-based format. They come in two types-- those owned by specific users (`Resource`) and those that are user-independent and associated with analysis operations (`OperationResource`). Examples of the latter include files for reference genomes, aligner indexes, or other analysis-specific files that a user does not need to maintain or directly interact with.

Much of the information regarding `Resource` instances is provided in the auto-generated docstring below, but here we highlight some key elements of the `Resource` model.  Namely, the kinds of operations users and admins can take to create, delete, or otherwise manipulated `Resource`s via the API.

**Resource creation**

- Regular MEV users can only create `Resource` instances by uploading files, either via a direct method (upload from local machine) or by using one our cloud-based uploaders (e.g. Dropbox). They can't do this via the API.

- Admins can "override" and create `Resource` instances manually via the API.

- Regardless of who created the `Resource`, the validation process is started asynchronously.  We cannot assume that the files are properly validated, even if the request was initiated by an admin.

- Upon creation of the `Resource`, it is immediately set to "inactive" (`is_active = False`) while we validate the particular type.

- `Resource` instances have a single owner, which is the owner who uploaded the file, or directly specified by the admin in the API request. `OperationResource`s do not have owners, but instead maintain a foreign-key relationship with their associated `Operation`.

**Resource "type" and "format"**

- To properly parse and validate a file, a `Resource` is required to have:
    - a "type" (e.g. an integer matrix) which we call a `resource_type`. This describes what the file represents (e.g. BED file, expression matrix, etc.). Upon creation, `resource_type` is set to `None` which indicates that the `Resource` has not been validated.
    - a "format" which tells us how the data is stored (e.g. TSV, CSV, Excel)

- We need *both* the type and format to proceed with validation.

- The type and format of the `Resource` can be specified immediately following the file upload or at any other time (i.e. users can change the type if they desire).  Each request to change type initiates an asynchronous validation process. Note that we can only validate certain types of files, like expression matrices. Validation of sequence-based files such as FastQ and BAM is not feasible and thus we skip validation.

- If the validation fails, we revert back to the previous successfully validated type and format.  If the type was previously `None` (as with a new upload), we simply revert back to `None` and inform the user the validation failed.

- Succesfully validated files are changed to a convenient internal representation. For instance, we accept expression matrices in multiple formats (e.g. CSV, TSV, XLSX). However, to avoid each analysis `Operation` from having to parse many potential file formats, we internally convert it to a consistent format, such as TSV. Thus, all the downstream tools expect that the validated resource passed as an input is saved in a TSV/tab-delimited format.

**Resources and metadata**

Depending on the type of `Resource`, we are able to infer and extract metadata from the file based on the format. For example, given a validated `Resource` that represents an RNA-seq count matrix, we assume that the column headers represent samples (`Observation`s) and the rows represent genes (`Feature`s). These metadata allow us to create subsets of the `Observation`s and `Feature`s for creating experimental contrasts and other typical analysis tasks. More on `Observation`s and `Feature`s is [described elsewhere.](elements.md)


**Resources and Workspaces**

- `Resource` instances are initially "unattached" meaning they are associated with their owner, but have *not* been associated with any user workspaces.

- When a user chooses to "add" a `Resource` to a `Workspace`, we append the `Workspace` to the set of `Workspace` instances associated with that `Resource`. That is, each `Resource` tracks which `Workspace`s it is associated with. This is accomplished via a many-to-many mapping in the database.

- Users can remove a `Resource` from a `Workspace`, but *only if it has NOT been used for any portions of the analysis*.  We want to retain the completeness of the analysis, so deleting files that are part of the analysis "tree" would create gaps.
Note that removing a `Resource` from a `Workspace` does not delete a file- it only modifies the `workspaces` field on the `Resource` database instance.


**Deletion of Resources**

- `Resource`s can only be deleted from the file manager on the "home" screen (i.e. not in the Workspace view) in the UI.

- If a `Resource` is associated/attached to one or more `Workspace`s, then you cannot delete the `Resource`. 

- A `Resource` can only be deleted if:
  - It is associated with zero `Workspace`s
  - It is not used in any `Operation`
Technically, we only need the first case. If a `Resource` has been used in an `Operation`, we don't allow the user to remove it from the `Workspace`. Thus, a file being associated with zero `Workspace`s means that it has not been used in any `Operation`s

**Notes related to backend implementation**

- In general, the `is_active = False` flag disallows any updating of the `Resource` attributes via the API.  All post/patch/put requests will return a 400 status.  This prevents multiple requests from interfering with an ongoing background process, such as validation.

- Users cannot change the `path` member.  The actual storage of the files should not matter to the users so they are unable to change the `path` member.


::: api.models.abstract_resource.AbstractResource
    :docstring:

::: api.models.resource.Resource
    :docstring:

::: api.models.operation_resource.OperationResource
    :docstring: