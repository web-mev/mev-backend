### Operation resources

For certain `Operation`s, we require data such as gene lists, gene-alias lookups, genome indices, and similar files which are not provided or owned by WebMEV users. Instead, these special `Resource`s are associated with the `Operation` they are used with. Suggestively, we call these `OperationResource` instances. Depending on the run-mode of the `Operation`, these `OperationResource`s are handled in different ways.

Regardless of the run-mode of the `Operation` (i.e. local, remote), we can handle these operation-specific resources in two ways. One method relies on the image container to hold the file. The other method requires WebMEV to "register" the `OperationResource` just as it does with user-associated `Resource`s .

The first method to distribute these user-independent files is to simply build them directly into the container. For small files, this solution is straightforward and does not require any special handling by WebMEV itself. For reproducing analyses, the versioned container image can always be pulled and run, ensuring the same files are used. Note that this assumes the files are "static" within that container and not dynamically queried/generated when the container is executed for an analysis operation. For instance, if the gene annotations, etc. are queried from BioMart on-the-fly *during* an analysis execution, then we can't necessarily guarantee 100% fidelity as the underlying data may change. On the other hand, if the files are created upon building/pushing the image, then those files can be safely distributed with the image and will remain unchanged within that image. 

Instead of building the files directly into the container image, one may also choose to create the files up front and then have WebMEV "register" them when the `Operation` is ingested. We do this by including an addition file (`operation_resources.json`) with the repository. This file gives the "name" of the file, its resource type (e.g. integer matrix, BED file, etc.), and the path to the file. For example, if we have an alignment process that depends on a pre-computed index, our `operation_spec.json` definition file would have an `OperationResource` input as follows:

```
{
    "name": "BWA alignment",
    ...
    "inputs": {
        ...
        "genome_index": {
            "description": "The genome to align to.", 
            "name": "Genome choice:", 
            "required": true, 
            "spec": {
                "attribute_type": "OperationResource",
                "resource_type": "*" 
            }
        }
        ...
    }
    ...
}
```
(the `resource_type` wildcard means "any" file type, which is fine for our purposes here). Then, in the same repository, we would have an `operation_resources.json` that looks like:

```
{
    "genome_index": [
        {
            "name": "Human",
            "resource_type": "*",
            "path": "gs://my-bucket/human_index.tar"
        },
        {
            "name": "Mouse",
            "resource_type": "*",
            "path": "gs://my-bucket/mouse_index.tar"
        }
    ]
}
```
Upon ingestion of this `Operation`, WebMEV will check for the presence of those files and, if present, will create database objects for these files. When the user wishes to run this `Operation`, those resources will be presented as the available options for that `genome_index` input. In accordance with our goal of reproducible research, the ingestion process copies the files to an operation-specific directory. Thus, given the `Operation`'s UUID, we will copy the file(s) to a storage location identified by that UUID. This way, we can prevent that original path from being overwritten or deleted over time.

Note that the path provided may either be "local" (e.g. `"path": "some_file.tsv"`) or remote (e.g. `"path": "gs://my-bucket/human_index.tar`). In the former case (where the path is relative or does not specify a "special" prefix like "gs://") WebMEV expects the file to be among the cloned repository files. Otherwise, we confirm the existence of the file using the appropriate libraries capable of interfacing with the remote storage systems. If the files are not found, then the ingestion of the `Operation` fails. 

The "repository-tracked" files are limited to relatively small files, however. Larger files, such as genome indexes which can be many GB, must be done using the remote storage option, which does require a bit more care to ensure everything is in-sync prior to ingestion. After ingestion, everything is properly versioned by reference to the `Operation`s UUID. 

As a final note, in the spirit of reproducible analyses, we advise that all scripts, etc. used to create the resource files are included in the repository or are otherwise adequately described. This is not something that can be enforced by WebMEV, but we aim to adhere with this guideline.