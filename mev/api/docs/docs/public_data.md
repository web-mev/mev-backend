### Working with public datasets

WebMeV provides the ability to easily create custom datasets derived from publicly available databases such as the Cancer Genome Atlas (TCGA). Query functionality of these datasets is exposed through Solr, which provides us a standard indexing and query syntax.

Given that each data repository has different formats and content, this functionality requires some custom code to create and manage the data on a case-by-case basis. In this guide, we describe the necessary elements to create/index a new data source.

In this guide, we will often refer to the TCGA RNA-seq as a prototypical example. This dataset contains count-based RNA-seq data downloaded from the NCI's genomic data commons (GDC) repository under the TCGA project.

### The quick way:

For convenience, there is a management command that handles most of the steps. Be sure to pay attention to the log messages, as they will direct you to change various things. If that script fails for whatever reason, we provide all the atomic details below.

Run the following in your Vagrant build:
```
python3 manage.py create_new_public_dataset \
    -d <core name>
    -f <path to an example file you want to index>
```

The core name (`-d`) should be relatively short/simple (e.g. `ccle-data`) and the the file (`-f`) should be an example of the data you wish to index. It can be a row subset (not ALL the data), but should have all the potential fields.

Note that the script will still require you to fill out the stubbed-out python module for the new dataset AND also require you to add some content to the Puppet manifests to fully integrate this new core.

You will also need to commit the solr files (`solr/<core>/schema.xml`  and `solr/<core>/solrconfig.xml`) when everything is fully ready.

---
### The longer way (or the way if the script above does not work!)


#### Step 1: Defining and creating the data

To create a new public dataset, we need to define how the data is collected and prepared. This section describes how to write the proper hooks for data ingestion and preparation.


**1.1 Create a new directory for your dataset**

To keep everything organized, we expect that each dataset will be kept in separate subdirectories of the `mev/api/public_data/sources` directory. However, note that there is no enforcement of this convention or any expected hierarchy of those subdirectories.

*Example:*
Note that `mev/api/public_data/sources` contains a `gdc` subdirectory and was created with the intent of holding all GDC projects; beyond TCGA, there are many other datasets exposed via the GDC repository. We expect that more of these GDC datasets will be included over time, so this was a logical way to structure the folder. You may choose to structure new datasets in an alternate manner.

The `gdc` directory contains several python modules which define how the GDC-derived datasets are to be downloaded and prepared. We define a `gdc.py` module which contains code expected to be common to all GDC projects. Code specific to preparation of TCGA data is contained in the `tcga.py` module. 

**1.2 Create an implementing class**

To provide a common means of ingesting/preparing all datasets, we expect that each dataset will be mapped 1:1 with a Python class that derives from `api.public_data.sources.base.PublicDataset`. This class requires the following:

- Class attributes:
    - `TAG`: This is a unique string which acts as an identifier for the dataset. If the name is not unique, then registering the dataset in the database will not be permitted, and hence the indexed dataset will not be usable. Additionally, the unit test suite will check that all implementing classes have unique identifiers. This string is limited to 30 characters by a database constraint.
    - `PUBLIC_NAME`: This string should be a relatively short "name" for the dataset, such as "TCGA RNA-seq"
    - `DESCRIPTION`: This is another string which provides more context and a thorough description of the data is contains.
- Methods:
    - `prepare(self)`: a method that takes no arguments (other than the class instance) and prepares the data. A return value is not expected.

A template for this new class:
```

from api.public_data.sources.base import PublicDataset

class MyDataset(PublicDataset):

    TAG = ''
    PUBLIC_NAME = ''
    DESCRIPTION = ''

    def prepare(self):
        pass
```

Note that you are not obligated to derive your implementation directly from `PublicDataset`; for the TCGA RNA-seq example, we created a hierarchy of `PublicDataset`-> `GDCDataSource` -> `TCGADataSource` -> `TCGARnaSeqDataSource` which reflects the fact that certain functionality is general to all GDC data sources and hence can be re-used if we incorporate other datasets from the GDC.

Also note that we make no requirements for the `prepare` method. In its simplest implementation, the dataset can be manually prepared and the `prepare` method can be left as an empty pass-through. This is the easiest option for datasets that are not actively updated or are difficult to automate. However, *you still need to define this implementing class, even if the implementation is trivial*.

More generally, the `prepare` method is the entry function for potentially many steps of data download and preparation. Again, while not enforced, we expect that the prepared data will ultimately be located under the `/data/public_data` directory so that it will be consistent with other data sources and can be persisted on redeployments. 

**1.3 "Register" the implementing class**

To allow WebMeV to "see" this new implementation, we have to add it to the `IMPLEMENTING_CLASSES` list in `api/public_data/__init__.py`. If this is not done, you will receive errors that will warn you of an unknown dataset.

#### Step 2: Define your solr core

The process of adding new cores for additional datasets is handled during provisioning and requires changes to the Puppet scripts. However, prior to that point, we need to create the proper files that will be used to create this new core. This section covers details of how to create these files.

To do this, below we will perform the following:

- Create a new (but ephemeral) Solr core
- Index an example file from your dataset using Solr's auto-detection functionality
- Query the auto-generated schema and edit it to ensure the inferred field types are correct. 

After these steps, we will have the necessary files which we can add to the WebMeV repository.  The provisioning process will then use those files to add the new core.

**2.1 Creating the core**

This step assumes you have a Vagrant-based system up and have SSH'd in. By default, you are the `vagrant` user.

**Important: the name of the Solr core you create MUST match the `TAG` attribute of your implementing class**. This is how the implementing class knows which Solr core to query.

Run:

`sudo -u solr /opt/solr/bin/solr create_core -c <core name>`

Solr should report that the new core was created.

#### Step 3: Obtaining and modifying the data schema

**3.1 Index an example file**

Above, Solr will create a default/schemaless core. For our purposes in WebMeV, the data is typically more structured and we have some notion of data structures and types in a given dataset (e.g. age as an integer type). Furthermore, we don't want to necessarily rely on Solr to properly guess the types of various fields.

Hence, we will first use Solr to auto-index an example file. Following this, we will request a "dump" of the current schema which we will subsequently edit to fit our needs. Ideally, the example file you use below is very close to the final data you are hoping to index (or *is* the data you want to expose). Mismatches between the schema and the data files will cause failures. 

To index the example file:
```
/opt/solr/bin/post -c <core name> <file path>
```

**3.2 Query for the current schema and edit**
Now, we will query for the current/inferred schema that was just created. Here, we put this in the `/vagrant/solr` directory, but it does not really matter where it goes, as long as you remember.

```
curl http://localhost:8983/solr/<core name>/schema?wt=schema.xml >/vagrant/solr/current_schema.xml
```
This `curl` request will provide the structured XML schema that is currently supporting the core.

At the top of the `current_schema.xml` file you will see many field type (`<fieldType>`) entries, which can be left as-is. You may, however, wish to remove those that are (likely) unnecessary. Examples include various tokenizer classes and filters corresponding to free-text analyzers and considerations for foreign language support. Those fields are not likely to be too relevant for most biomedical data we are analyzing within WebMeV. However, it is also fine to leave those all as-is.

You **will**, however, want to review and potentially make edits to the `<field>` entities located towards the tail of the schema. You should see field names corresponding to the columns/fields of the example file you indexed before. Depending on your data, you may choose to edit the `type` attributes. For instance, the default may be something like:
```
<field name="year_of_birth" type="pdoubles"/>
```
but we may wish to change that to integers:
```
<field name="year_of_birth" type="pint"/>
```
Similarly, many string-based fields default to a type of `text_general` which causes solr to initiate various NLP methods on these fields upon query. In most cases of biomedical data, these fields can better be indexed using a `string` type, which avoids unnecessary text processing. Values in `string` types are treated like enumerables (i.e. a finite set of strings) instead of a free text field that requires analysis. For example, in the TCGA dataset, we have a finite number of defined cancer types (e.g. TCGA-BRCA) that appear in the `project_id` field, thus, we can edit:

```
<field name="project_id" type="text_general"/>
```
to 
```
<field name="project_id" type="string"/>
```

Similarly, there will likely be many `<dynamicField>` and `<copyField>` entries which can be removed. These are added to enable further text processing that (usually) is not necessary and only increases the size of the index.

In the end, you should have a simple, human-interpretable list of fields that correspond to data types you recognize in the dataset. You *could* have created this all yourself, but Solr typically does a good job of guessing for most things.


#### Step 4: Copy the core files to the repository and commit

Recall that to create your core, we had to do a bit of a workaround above. The files defining your solr core are located in `/var/solr/data/<core name>`. We want to copy these files and our edited schema (AND remove the managed schema) to the WebMeV repository so that all the required items will be there for the new dataset. Hence:

```
cd /vagrant/solr
mkdir <core name>
cp /vagrant/solr/edited_schema.xml <core name>/schema.xml
cp /vagrant/solr/basic_solrconfig.xml <core name>/solrconfig.xml
```

At this point, the core files should be ready. You can commit these files to the repository.

#### Step 5: Add the core to your Puppet manifest

By adding the following snippet to your Puppet manifest at `deploy/puppet/mevapi/manifests/init.pp`, the provisioning step will create the necessary elements so that
your new core will be ready-to-go on the next round of provisioning:

Replace `<CORE>` below:
```
  solr::core { '<CORE>':
    schema_src_file     => "${project_root}/solr/<CORE>/schema.xml",
    solrconfig_src_file => "${project_root}/solr/<CORE>/solrconfig.xml",
  }
```

#### Step 6: Verify

To be sure that everything works, it's best to start a fresh local build. Since we manually created a new core and modified some of Solr's configuration files, we need to ensure our new dataset files work out of the box.

Destroy and re-created the VM however you wish. After, you can attempt to index a file into your new collection using the management commands we provide.

If you want to test the data download/preparation process, SSH into your VM and run
```
python3 manage.py pull_public_data -d <core name>
```

Then, to index a file into this core:
```
python3 manage.py index_data -d <core name> <path> [<path> ...]

```