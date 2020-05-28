### Resources

Much of the information regarding `Resource` instances is provided in the auto-generated docstring below, but here we highlight some key elements of the `Resource` model.  Namely, the kinds of operations users and admins can take to create, delete, or otherwise manipulated `Resource`s via the API.

**Resource creation**

- Regular MEV users can only create `Resource` instances by uploading files, either via a direct method (upload from local machine) or by using one our cloud-based uploaders. They can't do this via the API.

- Admins can "override" and create `Resource` instances manually via the API.

- Regardless of who created the `Resource`, the validation process is started asynchronously.  We cannot assume that the files are properly validated, even if the request was initiated by an admin.

- Upon creation of the `Resource`, it is immediately set to "inactive" (`is_active = False`) while we validate the particular type.

- `Resource` instances have a single owner, which is the owner who uploaded the file, or directly specified by the admin in the API request.

**Resource "type"**

- A `Resource` is required to have a "type" (e.g. an integer matrix) which we call a `resource_type`.  These types are restricted to a set of common file formats.  Upon creation, `resource_type` is set to `None` which indicates that the `Resource` has not been validated.

- The type of the `Resource` can be specified when the file is uploaded or at any other time (i.e. users can change the type if they desire).  Each request to change type initiates an asynchronous validation process.

- If the validation of the `resource_type` fails, we revert back to the previous successfully validated type.  If the type was previously `None` (as with a new upload), we simply revert back to `None` and inform the user the validation failed.

**Resources and Workspaces**

- `Resource` instances are initially "unattached" meaning they are associated with their owner, but have *not* been associated with any user workspaces.  Admins can, however, specify a `Workspace` in their request to create the `Resource` directly via the API.

- When a user chooses to "add" a `Resource` to a `Workspace`, a new database record is created which is a copy of the original, unattached `Resource` with the same attributes *except* the unique `Resource` UUID.  Thus, we have two database records referencing the same file.
We could accomplish something similar with a many-to-one mapping of `Workspace` to `Resource`s, but this was a choice we made which could allow for resource-copying if we ever allow file-editing in the future.  In that case, attaching a `Resource` to a `Workspace` could create a copy of the file such that the original `Resource` remains unaltered.
The user can, of course, change any of the *mutable* members of this new `Workspace`-associated `Resource`.  The changes will be independent of the original "unattached" `Resource`.

- Users can remove a `Resource` from a `Workspace` if it has NOT been used for any portions of the analysis.  We want to retain the completeness of the analysis, so deleting files that are part of the analysis "tree" would create gaps. 

**Deletion of Resources**

Since multiple database records can reference the same underlying file, we have a bit of custom logic for determining when we delete only the database record versus deleting the actual underlying file.  Essentially, if a deletion is requested and no other `Resource` database records reference the same file, then we delete *both* the database record AND the file.  In the case where there is another database record referencing that file, we only remove the database record, leaving the file.

**Notes related to backend implementation**

- In general, the `is_active = False` flag disallows any updating of the `Resource` attributes via the API.  All post/patch/put requests will return a 400 status.  This prevents multiple requests from interfering with an ongoing background process.

- Users cannot change the `path` member.  The actual storage of the files should not matter to the users so they are unable to change the `path` member.




::: api.models.resource.Resource
    :docstring: