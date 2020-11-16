## Documentation on the API

There are two aspects of the WebMEV backend.  

First, we have the public-facing RESTful API endpoints which are used to drive an analysis, upload files, and other actions.  Documentation of the API interaction is provided by auto-generated documentation conforming to the OpenAPI spec here: [API documentation](api_spec.html)  

The second aspect of WebMEV is the data structures, models, and concepts that we use to architect the system. You will find information about these entities and their relationships in this section.

### Core concepts

The goal of WebMEV is to provide a suite of analysis tools and visualizations to guide users through common analyses, most commonly with genomic (particularly transcriptomic) data. 

Users upload their own files or import data from selected public repositories. These data can then be manipulated within *workspaces*, which provide a way to separate out distinct analysis flows to keep a user's data and analyses organized.

One of the guiding principles within WebMEV is to provide transparent and reproducible analysis. As a result, the system is architected such that all analysis modules and workflows are available as standalone repositories; all code and supporting files are version-controlled and able to be executed independent of WebMEV (typically with containers such as Docker).

In accordance with this principle of reproducibility, WebMEV does not modify files in-place. That is, if a subset operation occurs, or crucial intermediate data is created, all those components are made available and are able to visualized as a tree structure. 


