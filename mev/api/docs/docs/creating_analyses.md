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
- `converters.json`
    - This file tells WebMEV how to take a user-supplied input (e.g. a list of samples/`Observation`s)
    and format it for the commandline invocation (e.g. as a comma-delimited list of strings)
- `entrypoint.txt`
    - This is a text file that provides a command template to be filled-in with the appropriate concrete arguments. The templating syntax is Jinja2 (https://jinja.palletsprojects.com)
- `docker/Dockerfile`
    - The `docker` folder contains (at minimum) a `Dockerfile` which provides the "recipe" for building the Docker image. Additional files to be included in the Docker build context (such as scripts) can be placed in this folder.

**Outputs**
While there are no restrictions on the nature or content of the analysis itself, we have to capture the analysis outputs in a manner that WebMEV can interpret those outputs and present them to end-users. Thus, we require that the process create an `outputs.json` file in the container's "workspace". This file is accessible to WebMEV via the shared volume provided with the `-v` argument to the `docker run` command. More details below in the concrete example.

Note that this is the only place where analysis code makes any reference to WebMEV. However, the creation of an `outputs.json` file does not influence the analysis code in any manner-- one could take an existing script, add a few lines to create the `outputs.json` and it would be ready for use as an analysis module in WebMEV.
    
#### Example

For this example, we look at the requirements for a simple principal component analysis (PCA). The repository is available at https://github.com/web-mev/pca/

We first describe the overall structure and then talk specifically about each file.

**Overall structure**

The repository has:
- `operation_spec.json` (required)
- `converters.json` (required)
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
            "spec": {
                "attribute_type": "DataResource", 
                "resource_types": ["MTX","I_MTX", "EXP_MTX", "RNASEQ_COUNT_MTX"], 
                "many": false
            }
        }, 
        "samples": {
            "description": "The samples to use in the PCA. By default, it will use all samples/observations.", 
            "name": "Samples:", 
            "required": false, 
            "spec": {
                "attribute_type": "ObservationSet"
            }
        }
    }, 
    "outputs": {
        "pca_coordinates": {
            "spec": {
                "attribute_type": "DataResource", 
                "resource_type": "MTX",
                "many": false
            }
        },
        "pc1_explained_variance": {
            "spec": {
                "attribute_type": "BoundedFloat",
                "min": 0,
                "max": 1.0
            }
        },
        "pc2_explained_variance": {
            "spec": {
                "attribute_type": "BoundedFloat",
                "min": 0,
                "max": 1.0
            }
        }
    }, 
    "mode": "local_docker"
}
```
In the `inputs` section, this `Operation` states that it has one required (`input_matrix`) and one optional input (`samples`). For `input_matrix`, we expect a single input file (a `DataResource` with `many=false`) that has an appropriate resource type. As PCA requires a numeric matrix (in our convention, with samples/observations in columns and genes/features in rows) we restrict these input types to one of `"MTX"`,`"I_MTX"`, `"EXP_MTX"`, or `"RNASEQ_COUNT_MTX"`. The full list of all resource types is available at `/api/resource-types/`

The second, optional input (`samples` ) allows us to subset the columns of the matrix to only include samples/observations of interest. The specification of this input states that we must provide it with an object of type `ObservationSet`. Recall, however, that our script is invoked by providing a comma-delimited list of sample names to the `-s` argument. Thus, we will use one of the "converter" classes to convert the `ObservationSet` instance into a comma-delimited string. This choice is left up to the developer of the analysis-- one could very well choose to provde the `ObservationSet` instance as an argument to their script and parse that accordingly.

For outputs, we expect a single `DataResource` with type `"MTX"` and two bounded floats, which represent the explained variance of the PCA.

**`converters.json`**

The `converters.json` file tells WebMEV how to take a user-input and convert it to the appropriate format to invoke the script. To accomplish this, we provide a mapping of the input "name" to a class which implements the conversion. For us, this looks like:
```
{
  "input_matrix":"api.converters.data_resource.LocalDockerSingleDataResourceConverter", 
  "samples": "api.converters.element_set.ObservationSetCsvConverter"
}
```
The class implementations are provided using Python's "dotted" notation. A variety of commonly-used converters are provided with WebMEV, but developers are free to create their own implementations for their own WebMEV instances. The only requirement is that the class implements a common interface method named `convert`, which takes the user-supplied input and returns an appropriate output.

As an example, we note that the `LocalDockerSingleDataResourceConverter` above takes the user-supplied input (a UUID which identifies a file/`Resource` they own) and "converts" it to a path on the server. In this way, the `run_pca.py` script is not concerned with how WebMEV stores files, etc. WebMEV handles the file moving/copying and analyses can be written without dependencies on WebMEV-related architecture or how files are stored within WebMEV.

The `samples` input uses the `api.converters.element_set.ObservationSetCsvConverter` which converts an `ObservationSet` such as:
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
into a CSV string: `sampleA,sampleB`.

Clearly, this requires some knowledge of the available "converter" implementations. We expect that there are not so many that this burden is unreasonable. We decided that the flexibility provided by this inconvenience was more beneficial than restricting the types of inputs and how they can be formatted for invoking jobs.

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

Create the `converters.json` file which will reformat the inputs into items that the entrypoint command will understand.

Once all these files are in place, create a git repository and check the code into github. The analysis is ready for ingestion with WebMEV.

---

### Remote, Cromwell-based jobs

TODO