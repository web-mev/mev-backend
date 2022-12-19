## Django management commands in WebMeV

There are several custom Django management commands available. For the most part, these are used by processes such as provisioning scripts. However, there are several that are actively used by WebMeV admins. We list these below and note what they do and how they are used.

All of these are initiated using the standard Django `python3 manage.py <command>` calls. Help for each can be found by appending the `-h` flag.

### Commands for working public datasets

WebMeV provides these commands for managing public datasets (e.g. TCGA) within the application. Rather than relying on cron jobs or other periodic mechanisms for data import/indexing, we provide these commands so admins can actively manage these datasets.

#### `pull_public_data`

This command calls the underlying implementation for a given public dataset. Provide the unique string identifier to start the data download/processing:

```
usage: manage.py pull_public_data -d DATASET_ID
```
This command only performs download and data munging- it does not modify any database tables or expose any new datasets. It only handles the preparation of the data that will ultimately be indexed in another step.

Note that each public dataset has, in general, different formats and requirements. We expect that the implementation of this command for each public dataset will appropriately inform the admin of its actions and any output files. For instance, the TCGA dataset icreates two files- a metadata file and a count matrix.

#### `index_data`

This command will index one or more flat files into the specified dataset. This command modifies the database so that it's available for querying and usage.

```
usage: manage.py index_data -d DATASET_ID <key=value> [<key=value>] ...
```
where the >=1 key-value pairs are specific to the dataset we are indexing. Those parameters tell the indexing process the identity of the files. Recall that each dataset will have different requirements and files, in general. 

As an example, consider the TCGA RNA-seq dataset. Here, the `pull_public_data` command prepares a HDF5-format file of gene expression counts *and* a CSV-format file of sample annotations. To index RNA-seq data from TCGA (and most RNA-seq datasets), we would run:

```
manage.py index_data -d tcga-rnaseq annotations=<path to annotation CSV file> counts=<path to HDF5 file>
```
For the TCGA dataset, our process knows to look for these two key-value pairs. It knows to use the value paired with the `annotations` key as the file for indexing by Solr. The database then tracks both of these files so that we can query and prepare datasets for users. 

Note that this assumes a "core" (in solr parlance) already exists for the dataset; typically these are created during machine provisioning. Since each dataset requires some amount of manual curation, we still have to do the work of understanding each dataset and preparing the necessary Solr core files.


### Other commands


#### `add_static_operations`

This is used to add "static" operations like file transfers (e.g. the Drobox+Cromwell flow) to the application. This is different than the "dynamic" analysis operations that are added after the WebMeV application is running. This is typically called by the provisioning script and does not need to be run manually.

In principle, one could choose to amend this script to automatically ingest a set of analysis applications.

#### `build_docs`

This command creates this documentation. If the `--push` flag is added, then the documentation will be pushed to github to the `gh-pages` branch. By default, it is *not* pushed so you can inspect the pages locally.

#### `dump_db_for_test`

This is a thin wrapper around the Django `dumpdata` command, which will dump the contents of the database models under `api` to a JSON file. That data can then be used for the test suite. Note that the repository includes a `api/tests/test_db.json` file, so this command would typically be run by a developer to add new data to the test database.

#### `populate_db`

This command will add some dummy data to the database. The data added are a minimum set of database records that will allow for unit testing. 

As mentioned, the repository includes a test database file at `api/tests/test_db.json`. However, one could instead use this command to populate the database with new data, then subsequently use the `dumb_db_for_test` command above to create a new `api/tests/test_db.json` file.