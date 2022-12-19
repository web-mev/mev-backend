## Creating a new analysis (`Operation`) for use with WebMEV

WebMEV analyses (AKA `Operation`s) are designed to be transparent and portable. While certain files are required for integration with the WebMEV application, the analyses are designed so that they are self-contained and can be transparently reproduced elsewhere. 

Depending on the nature of the analysis, jobs are either executed locally (on the WebMEV server) or remotely on ephemeral hardware that is dynamically provisioned from the cloud computing provider. Thus, the "run mode" of the analyses affects which files are required for WebMEV integration. Below, we describe the architecture of WebMEV-compatible analyses and how one can go about creating new ones.

--- 

### Local Docker-based mode

Typically, local Docker-based jobs are used for lightweight analyses that require a minimal amount of hardware. Examples include principal-component analyses, differential expression testing, and other script-based jobs with relatively modest footprints.

Local Docker-based jobs are intended to be invoked like a standard commandline executable or script. Specifically, to run the job, we start the Docker container with a command similar to:
```
docker run -d -v <docker volume>:<container workspace> --entrypoint=<CMD> <IMAGE>
```
This runs the command specified by `<CMD>` in the environment provided by the Docker image. In this way, we isolate the software dependencies of the analysis from the host system and provide users a way to recreate their analysis at a later time, or to independently clone the analysis repository and run it on any Docker-capable system. 

To construct a WebMEV-compatible analysis for local-Docker execution mode, we require the following files be present in a repository:

- `operation_spec.json`
    - This file dictates the input and output parameters for the analysis. Of type `Operation`.
- `entrypoint.txt`
    - This is a text file that provides a command template to be filled-in with the appropriate concrete arguments. The templating syntax is Jinja2 (https://jinja.palletsprojects.com)
- `docker/Dockerfile`
    - The `docker` folder contains (at minimum) a `Dockerfile` which provides the "recipe" for building the Docker image. Additional files to be included in the Docker build context (such as scripts or static data) can be placed in this folder.

**About container registries and Docker images for local jobs**

You can distribute your Docker images in a couple of ways, but they ultimately must be located in a public Docker repository where WebMEV (and others!) can find and pull them. At the current time, you must choose one method for all your local analysis tools. That is, you can't have one tool pull from Dockerhub while another uses Github. There are two options here, currently:

- (preferred and current default) Configure Github Actions to build your Docker image automatically upon each commit. This requires the use of a Github Actions yaml file which can be added to the repository; see the other WebMEV tool repositories and/or look at Github actions docs. As configured for the currently available tools, the script builds the image with the following name format: `<github-org>/<repository-name>:<commit hash>`. Then, the image will be available at `ghcr.io/<github-org>/<repository-name>:<commit hash>`. The advantage of this method is that everything is contained in a single github repository and there is a lesser chance of the built image drifting from that specified in `docker/Dockerfile`.

- Manually build and push your Docker images (based off `docker/Dockerfile`) to Dockerhub in a public account. If you do this, then you must configure WebMEV to use Dockerhub (change the `container_registry` setting to `"dockerhub"` in  `deployment-aws/puppet/mevapi/manifests/init.pp`). This requires a manual build, however, which requires an extra step and can result in differences between the committed `docker/Dockerfile` and the one used to build the image. 

Note that depending on the `container_registry` setting, the workflow ingestion scripts will expect a certain container repository. For example, with the default setting of `"github"`, the image URI will be prefixed by `"ghcr.io"`.

**Outputs**
While there are no restrictions on the nature or content of the analysis itself, we have to capture the analysis outputs in a manner that WebMEV can interpret those outputs and present them to end-users. Thus, we require that the process create an `outputs.json` file in the container's "workspace". This file is accessible to WebMEV via the shared volume provided with the `-v` argument to the `docker run` command. More details below in the concrete example.

Note that this is the only place where analysis code makes any reference to WebMEV. However, the creation of an `outputs.json` file does not influence the analysis code in any manner-- one could take an existing script, add a few lines to create the `outputs.json` and it would be ready for use as an analysis module in WebMEV.
    
#### Example

For this example, we look at the requirements for a simple principal component analysis (PCA). The repository is available at https://github.com/web-mev/pca/

We first describe the overall structure and then talk specifically about each file.

**Overall structure**

The repository has:
- `operation_spec.json` (required)
- `entrypoint.txt` (required)
- `docker/`
    - `Dockerfile` (required)
    - `run_pca.py`
    - `requirements.txt`

The analysis is designed so that it will execute a single python script (`docker/run_pca.py`) as follows:

```
run_pca.py -i <path to input file> [-s <comma-delimited list of sample names>]
```
The first arg (`-i`) provides a path to an input matrix (typically an expression/abundance matrix). The second (optional) argument (`-s`) allows us to specify sample names to use, formatted as a comma-delimited list of samples. By default (if no argument provided) all samples are used.

In addition to running the PCA, this script will also create the `outputs.json` file. It's not required that you structure the code in any particular manner, but the analysis has to create the `outputs.json` file at some point before the container exits. Otherwise, the results will not be accessible for display with WebMEV.

**`docker/` folder and Docker context**

In the `docker/` folder we have the required `Dockerfile`, the script to run (`run_pca.py`), and a `requirements.txt` file which provides the packages needed to construct the proper Python installation.

The `Dockerfile` looks like:
```
FROM debian:stretch

RUN apt-get update && \
    apt-get install -y python3-dev python3-pip

# Install some Python3 libraries:
RUN mkdir /opt/software
ADD requirements.txt /opt/software/
ADD run_pca.py /opt/software/
RUN chmod +x /opt/software/run_pca.py
RUN pip3 install -r /opt/software/requirements.txt

ENTRYPOINT ["/opt/software/run_pca.py"]
```

`requirements.txt` looks like: (truncated)
```
cryptography==1.7.1
...
scikit-learn==0.22.2.post1
...
scipy==1.4.1
...
```

`run_pca.py`:
For brevity, we omit the full `run_pca.py` script (available at https://github.com/web-mev/pca/blob/master/docker/run_pca.py), but note that the `Dockerfile` places this script in the `/opt/software` folder. Thus, we have to either append to the `PATH` in the container, or provide the full path to this script when we invoke it for execution. Below (see `entrypoint.txt`) we use the latter.

Finally, we note that this script creates an `outputs.json` file:
```
...
outputs = {
    'pca_coordinates': <path to output matrix of principal coordinates>,
    'pc1_explained_variance':pca.explained_variance_ratio_[0],
    'pc2_explained_variance': pca.explained_variance_ratio_[1]
}
json.dump(outputs, open(os.path.join(working_dir, 'outputs.json'), 'w'))
```

As stated prior, it's not required that *this* script create that file, but that the file be created at some point before the container exits. This is the only place where scripts are required to "know about WebMEV". Everything else in the script operates divorced from any notion of WebMEV architecture. 



**`operation_spec.json`**

The operation_spec.json file provides a description of the analysis and follows the format of our `Operation` data structure:
```
{
    "name": "", 
    "description": "", 
    "inputs": <Mapping of keys to OperationInput objects>, 
    "outputs": <Mapping of keys to OperationOutput objects>, 
    "mode": ""
}

```
Importantly, the `mode` key must be set to `"local_docker"` which lets WebMEV know that this analysis/`Operation` will be run as a Docker-based process on the server. Failure to provide a valid value for this key will trigger an error when the analysis is "ingested" and prepared by WebMEV.

Concretely our PCA analysis:
```
{
    "name": "Principal component analysis (PCA)", 
    "description": "Executes a 2-d PCA to examine the structure and variation of a dataset.", 
    "inputs": {
        "input_matrix": {
            "description": "The input matrix. For example, a gene expression matrix for a cohort of samples.", 
            "name": "Input matrix:", 
            "required": true, 
            "converter": "api.converters.data_resource.LocalDockerSingleVariableDataResourceConverter",
            "spec": {
                "attribute_type": "VariableDataResource", 
                "resource_types": ["MTX","I_MTX", "EXP_MTX", "RNASEQ_COUNT_MTX"], 
                "many": false
            }
        }, 
        "samples": {
            "description": "The samples to use in the PCA. By default, it will use all samples/observations.", 
            "name": "Samples:", 
            "required": false, 
            "converter": "api.converters.element_set.ObservationSetCsvConverter",
            "spec": {
                "attribute_type": "ObservationSet"
            }
        }
    }, 
    "outputs": {
        "pca_coordinates": {
            "required": true,
            "converter": "api.converters.data_resource.LocalDockerSingleDataResourceConverter",
            "spec": {
                "attribute_type": "DataResource", 
                "resource_type": "MTX",
                "many": false
            }
        },
        "pc1_explained_variance": {
            "required": true,
            "converter": "api.converters.basic_attributes.FloatConverter",
            "spec": {
                "attribute_type": "BoundedFloat",
                "min": 0,
                "max": 1.0
            }
        },
        "pc2_explained_variance": {
            "required": true,
            "converter": "api.converters.basic_attributes.FloatConverter",
            "spec": {
                "attribute_type": "BoundedFloat",
                "min": 0,
                "max": 1.0
            }
        }
    }, 
    "mode": "local_docker",
    "workspace_operation": true
}

```
In the `inputs` section, this `Operation` states that it has one required (`input_matrix`) and one optional input (`samples`). For `input_matrix`, we expect a single input file (a `VariableDataResource` with `many=false`); the `VariableDataResource` permits multiple resource types. As PCA requires a numeric matrix (in our convention, with samples/observations in columns and genes/features in rows) we restrict these input types to one of `"MTX"`,`"I_MTX"`, `"EXP_MTX"`, or `"RNASEQ_COUNT_MTX"`. The full list of all resource types is available at `/api/resource-types/`

The second, optional input (`samples` ) allows us to subset the columns of the matrix to only include samples/observations of interest. The specification of this input states that we must provide it with an object of type `ObservationSet`. Recall, however, that our script is invoked by providing a comma-delimited list of sample names to the `-s` argument. Thus, we will use the `api.converters.element_set.ObservationSetCsvConverter` "converter" class to convert the `ObservationSet` instance into a comma-delimited string. This choice is left up to the developer of the analysis-- one could very well choose to provde the `ObservationSet` instance as an argument to their script and parse that accordingly. 

As a concrete example of the converter, consider the following `ObservationSet`:
```
{
    "elements": [
        {
            "id":"sampleA",
            "attributes": {}
        },
        {
            "id":"sampleB",
            "attributes": {}
        }    
    ]
}
```
The `api.converters.element_set.ObservationSetCsvConverter` class will take that data structure and return a comma-delimited string. In this case, `"sampleA,sampleB"`.


For outputs, we expect a single `DataResource` with type `"MTX"` and two bounded floats, which represent the explained variance of the PCA.

**`entrypoint.txt`**

The entrypoint file has the command that will be run as the `ENTRYPOINT` of the Docker container. To accommodate optional inputs and permit additional flexibility, we use jinja2 template syntax.

In our example, we have:
```
/opt/software/run_pca.py -i {{input_matrix}} {% if samples %} -s {{samples}} {% endif %}
```
(as referenced above, note that we provide the full path to the Python script. Alternatively, we could put the script somewhere on the `PATH` when building the Docker image)

The variables in this template (between the double braces) must match the keys provided in the `inputs` section of the `operation_spec.json` document.

Thus, if the `samples` input is omitted (which means all samples are used in the PCA calculation), the final command would look like:
```
/opt/software/run_pca.py -i <path to matrix>
```
If the `samples` input is provided, WebMEV handles converting the `ObservationSet` instance into a comma-delimited string to create:
```
/opt/software/run_pca.py -i <path to matrix> -s A,B,C
```
(e.g. for samples/observations named "A", "B", and "C")


#### A suggested workflow for creating new analyses

First, without consideration for WebMEV, consider the expected inputs and outputs of your analysis. Generally, this will be some combination of files and simple parameters like strings or numbers. Now, write this hypothetical analysis as a formal `Operation` into the `operation_spec.json` file. 

Create a Dockerfile and corresponding Docker image with and an analysis script that is executable as a simple commandline program. Take care to include some code to create the `outputs.json` file at some point in the process. 

Take the "prototype" command you would use to execute the script and write it into `entrypoint.txt` using jinja2 template syntax. The input variable keys should correspond to those in your `operation_spec.json`. 

Once all these files are in place, create a git repository and check the code into github. The analysis is ready for ingestion with WebMEV.

---

### Remote, Cromwell-based jobs

For jobs that are run remotely with the help of the Cromwell job engine, we have slightly different required files. 

Cromwell-based jobs are executed using "Workflow Definition Language" (WDL) syntax files (https://openwdl.org/). When using this job engine, the primary purpose of WebMEV is to validate user inputs and reformat them to be compatible with the inputs required to run the workflow. For those who have not used Broad's Cromwell engine before, the three components of an analysis workflow include:

- WDL file(s): Specifies the commands that are run. You can think of this as you would a typical shell script.
- A JSON-format inputs file: This maps the expected workflow inputs (e.g. strings, numbers, or files) to specific values. For instance, if we expect a file, then the inputs JSON file will map the input variable to a file path. WebMEV is responsible for creating this file at runtime.
- One of more Docker containers: Cromwell orchestrates the startup/shutdown of cloud-based virtual machines but all commands are run within Docker runtimes on those machines. Thus, the WDL files will dictate which Docker images are used for each step in the analysis. There can be an arbitrary number of these. Furthermore, unlike the local Docker-based jobs which require a single image, these jobs can use multiple images which can be placed in any combination of public Docker repositories (Dockerhub, Github CR, quay.io).


Thus, to create a Cromwell-based job that is compatible with WebMEV we require: 

- `operation_spec.json`
    - This file dictates the input and output parameters for the analysis. Of type `Operation`. This file is the same as with any WebMEV analysis. To specifically create an `Operation` for the Cromwell job runner, you *must* specify `"mode": "cromwell"` in the `Operation` object.

- `main.wdl`
    - In general there can be any number of WDL-format files in the repository. However, the primary or "entry" WDL file *must* be named as `main.wdl`.

- `inputs.json`
    - This is the JSON-format file which dictates the inputs to the workflow. It is a template that will be appropriately filled at runtime. Thus, the "values" of the mapping do not matter, but the keys must map to input variables in `main.wdl`. Typically, this file is easily created by Broad's WOMTool. See below for an example.

- `docker/`
    - The `docker` folder contains one or more Dockerfile-format files and the dependencies to create those Docker images.

#### Additional notes:


**Remarks about dependencies between `main.wdl`, `inputs.json` and `operation_spec.json`**

As much as we try to remove interdependencies between files (for ease of development), there are situations we can't resolve easily. One such case is the interdependencies between `main.wdl`, `inputs.json`, and the `operation_spec.json` files.

As mentioned above, the `inputs.json` file supplied in the repository is effectively a template which is filled at runtime. The keys of that object correspond to inputs to the main WDL script `main.wdl`. For example, given a WDL script with the following input definition:
```
workflow SomeWorkflow {
    ...
    Array[String] samples
    ....
}
```

then the `inputs.json` would require the key `SomeWorkflow.samples`. Generally, WDL constructs its inputs in the format of `<Workflow name>.<input variable name>`. Thus, `inputs.json` would appear, in part, like

```
{
    ...
    "SomeWorkflow.samples": "Array[String]",
    ...
}
```
As mentioned above, the "value" (here, `"Array[String]"`) does not matter; Broad's WOMTool will typically fill-in the expected type (as a string) to serve as a cue.

Finally, WebMEV has to know which inputs of the `Operation` correspond to which inputs of the WDL script. Thus, in our `operation_spec.json`, the keys in our `inputs` object must be consistent with `main.wdl` and `inputs.json`:

```
{
    ...
    "inputs": {
        ...
        "SomeWorkflow.samples": <OperationInput>
        ...
    }
}
```

**Converting inputs**

As with all analysis execution modes, we have "converter" classes (specified in `operation_spec.json`) which translate user inputs into formats that are compatible with the job runner. 

For instance, using the example above, one of the inputs for a WDL could be an array of strings (`Array[String]` in WDL-type syntax). Thus, a converter would be responsible for taking say, an `ObservationSet`, and turning that into a list of strings to provide the same names. For example, we may wish to convert an `ObservationSet` given as:

```
{
    "multiple": true,
    "elements": [
        {
            "id":"sampleA",
            "attributes": {}
        },
        {
            "id":"sampleB",
            "attributes": {}
        }    
    ]
}
```
Then, the "inputs" data structure submitted to Cromwell (basically `inputs.json` after it has been filled-in) would, in part, look like:
```
{
    ...
    "SomeWorkflow.samples": ["sampleA", "sampleB"],
    ...
}
```

**Creation of Docker images**

As described above, each repository can contain an arbitrary (non-zero) number of WDL files, each of which can depend on one more Docker images for their runtime. In contrast to local jobs which can only use a single image, WDL/Cromwell-based jobs can use any number of images. However, there are some custom steps involved during the ingestion of new Cromwell-based workflow, which we explain below.

When Docker images are specified in the `runtime` section of the WDL files, the line is formatted as:

```
runtime {
    ...
    docker: "<repo name>/<username>/<image name>:<tag>"
    ...
}
```
e.g.

```
runtime {
    ...
    docker: "docker.io/myUser/foo:v1"
    ...
}
```

**When using pre-built Docker images:**
Recall that if there is no explicit image "tag", then Docker defaults to using the image with the "latest" tag, which is implicitly the last build. Thus, if you are using an external Docker image (e.g. biocontainers/samtools) for one of your WDL tasks, then be sure to pick a specific tagged version so that it is not ambiguous, since `latest` can change over time.

**When creating our own Docker images:**

As mentioned in the local tools section, by default we use Github Actions to automatically build Docker images off the current repository state. The images are tagged with the github commit hash.

If you have configured WebMEV to use the Dockerhub repo by default, then just be sure to build/tag/push your images carefully. That is, if you use `docker: "docker.io/myUser/foo:v1"` in your WDL, you need to name+tag your image, e.g. `docker build -t myUser/foo:v1`.

When using a custom Docker image built directly by Github Actions, we have a bit of a "chicken or egg" problem when it comes to providing tagged Docker images in our WDL files. As configured, Github Actions tags the Docker image with the commit hash. However, we obviously can't know that hash up front and use it in our WDL file(s). Hence, we reference untagged images in the `docker` attribute as follows:
```
runtime {
    ...
    docker: "ghcr.io/web-mev/mev-hcl"
    ...
}
```

As part of the process of ingesting analysis tools into WebMEV, we modify that `docker` WDL attribute to attach a tag corresponding to the git commit. The process is roughly:

- Parse all WDL files in the github repo and extract out all the runtime Docker images. This will be a set of strings.
- For each Docker untagged "image string" (e.g. `ghcr.io/someUser/foo`):
    - Get the current git commit (say, `abc123`) and append that (e.g. `ghcr.io/someUser/foo:abc123`)
    - Search for that image. If it does not exist, fail the ingestion process. This effectively prevents untagged images from being used. For instance, if an untagged `docker.io/biocontainers/samtools` Docker image was specifed, the full, tagged image would be `docker.io/bioco`ntainers/samtools:abc123`. There is a vanishingly small chance that our git repository's commit hash has a corresponding tag in the `biocontainers/samtools` library. 
- For each tagged "image string" (e.g. `docker.io/biocontainers/samtools:v1.9-4-deb_cv1`), simply search for it.

We note that this technically modifies the workflow relative to the github repository, so the WebMEV-internal version is not *exactly* the same. However, this difference is limited to the name of the Docker image. All other aspects of the analysis are able to be exactly recreated based on the repository.

**Copying of static resources**

If the `static_inputs.json` file is present, we expect that this file will be used for static items that are not dependent on user input. We could also put such items as `default` in the `operation_spec.json` file, but we instead choose to extract them out to this file.

At current, no tools use this feature, but this will be updated if necessary.

