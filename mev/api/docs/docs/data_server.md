### Using the WebMeV backend as a local data server

The purpose of this document is to describe the process for creating a local WebMeV API that contains all the relevant operations and result files such that a frontend application can develop against actual output files and interact just as one might with a real, production server.

The motivation for this is that backend analysis tools and frontend dev typically happens in parallel. When a new tool is created, the frontend needs access to the specific output/result files for developing the new results page and visualization. Unforunately, due to the complexities of some of the analyses and how they are run (e.g. locally run or remotely via Cromwell), it's not always feasible to run a fully-featured, local API server. For example, the local machine may not have sufficient resources to run a particular analysis. Further, it is faster to develop the frontend with a set of well-defined outputs to use.

Hence, what we describe here will create an API server which has "pre-baked" results which can be served to a frontend application.

Note that the purpose of the data server is NOT to run analyses, although it is technically possible provided you are running "local" (i.e. Docker-based analyses) on your local machine.

Finally, also note that the data export described below can export a large amount of data, depending on how many users are actively using your WebMeV deployment. Thus, for a smaller storage footprint, it may be advisable to first generate a new cloud-based deployment with a minimal set of operations and results specific to your frontend development effort.

#### Instructions

The first step is extract the data from another deployment (e.g. production) which has operations and results you wish to import. For that, we have a helper script in `etc/extract_data.sh`. It takes five commandline args in order:

- **Database ID:** This is the string identifier for the database *instance* you are extracting data from. You can find this either from your terraform deployment, by browsing to the SQL area of the Google web console, or by executing the following gcloud command: `gcloud sql instances list`. We are looking for the string identifier in the first, `NAME` column.

- **Database name:** This is the name of the database created on the instance above. This is the postgres database you are creating as part of the provisioning scripts.

- **GCP zone:** This is the zone (e.g. us-east4-c) where the compute instance (the VM serving the API you are extracting data from) is located.

- **GCP compute instance:** This is the name of the VM hosting the API

- **API storage bucket:** The cloud-based API stores all user files in a storage bucket. We need to copy those files, so this variable is the name, *without the `gs://` prefix*, of that bucket.

Run the script:
```
etc/extract_data.sh <DB ID> <DB name> <zone> <GCP VM name> <Bucket name>
```
and it will perform all the data extraction and copying. It will place all the necessary files into a new bucket, which it will print to your console, `gs://mev-data-export-<UUID>`.

#### Downloading the extracted data/results

First, we need to download the data we just extracted. The Vagrant-based provisioning script expects that we are locating this data in a folder named `example_data` at the root of the project (i.e. as a sibling of your Vagrantfile). If not there already, make a directory:
```
cd mev-backend
mkdir example_data
```
then, change into that directory and use `gsutil` to copy everything:
```
cd example_data
gsutil -m cp -r gs://<YOUR EXPORT BUCKET>/* .
```
Note that the `-m` flag is optional, but allows faster, parallel downloads.

When the download is complete, you should have three items in this `example_data` folder:

- db_export.gz
- user_resources/
- operations/

Both `user_resources/` and `operations/` are folders with further subdirectories.

#### Preparing your local development instance for this data


To populate our development instance with this data, we need to tell the Vagrant provisioning script that we wish to populate our local instance with an existing database dump and some result files. 

To do this, we simply set `RESTORE_FROM_BACKUP=yes` in `vagrant/env.txt`. If you set this variable to anything but `"yes"`, then it will *NOT* work. Also note that setting this variable will effectively ignore the `POPULATE_DB` variable which is typically used for creating fake/dummy data in a dev environment.

Then, as part of the provisioning process, we have two scripts (written as Django command hooks) which 1) edits the database and 2) moves the operation folders to the appropriate locations. 

When editing the database, the script updates all the resource paths to reference the local, filesystem based files instead of the bucket-based objects. Further, the database editing script assigns ownership of all files and executed operations to the superuser account created as part of the provisioning.

#### Potential pitfalls

One potential pitfall is that if you run the provisioning script multiple times, you need to repopulate the test data directly from the bucket. Otherwise, the referenced paths and database dump will have been changed and we cannot guarantee the integrity of the `example_data/` folder.





