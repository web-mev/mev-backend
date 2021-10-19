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

This command will index one or more flat files into the specified dataset

```
usage: manage.py index_data -d DATASET_ID path [path ...]
```

Note that this assumes a "core" (in solr parlance) already exists for the dataset; typically these are created during machine provisioning. The files to index should be amenable to the XML schema defining that core. Files should also be one of the formats that indexing technology (solr) understands, such as CSV.

Use of this command requires some knowledge of how the data will be exposed via the public dataset query interface. For instance, in the case of TCGA RNA-seq data, we create two files using the `pull_public_data` command above. However, this indexing step will only work with CSV-format metadata file. After all, we are using the indexer to provide a means to query/search datasets for appropriate data. Attempting to index the count file would likely break the process and realistically not make much sense.


### Other commands


#### `add_static_operations`

This is used to add "static" operations like file transfers (e.g. the Drobox+Cromwell flow) to the application. This is different than the "dynamic" analysis operations that are added after the WebMeV application is running. This is typically called by the provisioning script and does not need to be run manually.

In principle, one could choose to amend this script to automatically ingest a set of analysis applications.

#### `build_docs`

This command creates this documentation. If the `--push` flag is added, then the documentation will be pushed to github to the `gh-pages` branch. By default, it is *not* pushed so you can inspect the pages locally.

#### `dump_db_for_test`

This is a thin wrapper around the Django `dumpdata` command, which will dump the contents of the database models under `api` to a JSON file. That data can then be used for the test suite. Note that the repository includes a `api/tests/test_db.json` file, so this command would typically be run by a developer to add new data to the test database.

#### `edit_db_data`

This is used if you would like to stand up a mock server that has some data prepopulated. The script modifies database records (e.g. changing the ownership of files) accordingly.

The motivation for this command was to allow us to create a backend instance to be used by a frontend developer. In that case, we would like to provide "real" data they can use for visualizations. However, we can't simply export data from, for instance, our production server since the resources, etc. would be owned by user accounts only present on the production system. This command handles the modification of database records to hand over ownership to a single user. 

#### `populate_db`

This command will add some dummy data to the database. The data added are a minimum set of database records that will allow for unit testing. 

As mentioned, the repository includes a test database file at `api/tests/test_db.json`. However, one could instead use this command to populate the database with new data, then subsequently use the `dumb_db_for_test` command above to create a new `api/tests/test_db.json` file.