## Documentation on the API

There are two aspects of the WebMEV backend.  

First, we have the public-facing RESTful API endpoints which are used to drive an analysis, upload files, and perform other actions.  Documentation of the API is provided by auto-generated documentation conforming to the OpenAPI spec here: [API documentation](api_spec.html).

The second aspect of WebMEV is the data structures, models, and concepts that we use to architect the system. You will find information about these entities and their relationships in this section. Understanding these data structures and associated nomenclature will be important when describing how to work with WebMEV and create new workflows.

### Core concepts

The goal of WebMEV is to provide a suite of analysis tools and visualizations to guide users through self-directed analyses, most commonly with genomic (particularly transcriptomic) data. 

At a high level, users will start from either files that they provide (e.g. a previously generated expression matrix) or (if available) can import data from public repositories that are available through WebMEV. Users will then create one or more `Workspace`s which facilitates logical organization of analyses and separation of distinct projects or experiments. Within the context of the `Workspace`, users can perform a custom analysis as a series of atomic steps which we call `Operation`s.

More specific details about each of these steps, including how we handle metadata are available in the other sections of this documentation.

<!-- Once files are uploaded, users can declare the expected file "type"s; for instance, they might declare that a particular file corresponds to an RNA-seq expression matrix. The WebMEV backend will attempt to check the integrity of these files, namely that they conform to our formatting expectations. To prevent potential issues in downstream analysis tools, we require strict adherence to our expected formatting. 

Within the WebMEV code, files are referred to as `Resource`s. A `Resource` may either be associated with a user ("owned" by that user) or is user-independent, but associated with an analysis operation (an `OperationResource`). An example of an `OperationResource` is a genome index for an alignment process; users should not be responsible for these process-specific `OperationResource`s, so we associate them directly with the 

Users may then begin to analyze their data in the context of 

**Users**
To track usage and better diagnose potential problems, we require that all users register with WebMEV; anonymous usage is not permitted. Users are identified by their email address but may choose to register by using their email/password *or* by using one of the third-party identity providers (e.g. Google).

**User-p
Users upload their own files or import data from selected public repositories as they are made available. These data can then be manipulated within *workspaces*, which provide a way to separate out distinct analysis flows to keep a user's data and analyses organized.

One of the guiding principles within WebMEV is to provide transparent and reproducible analysis. As a result, the system is architected such that all analysis modules and workflows are available as standalone repositories; all code and supporting files are version-controlled and able to be executed independent of WebMEV (typically with containers such as Docker).

In accordance with this principle of reproducibility, WebMEV does not modify files in-place. That is, if a subset operation occurs, or crucial intermediate data is created, all those components are made available and are able to visualized as a tree structure.  -->


