## General architecture of WebMEV

WebMEV is a Django-based RESTful API web application with the following components:

![](arch.svg)

Components located within the dotted outline are *always* located on the same server. Their roles are:

- The nginx server accepts requests on port 80. If the request is for static content (resources such as CSS files located at `/static/`) then nginx will directly respond to the request. Note that there are minimal CSS and JS static files associated with Django Rest Framework's browsable API. It is expected that the API will be accessed with an appropriate frontend and thus there are minimal static files related to rendering user interfaces. 

- The gunicorn application server handles non-static requests and is the interface between nginx and Django. These connect through a unix socket.


**For the database**
- We use a postgres database to store information about users, their files and workspaces, and metadata about the analysis operations and their executions. *Depending on the deployment environment, the postgres server is implemented either on the host machine or using a cloud-based service*. 
    - For local, Vagrant/virtualbox-based deployments, postgres is directly installed on the host VM.
    - For cloud-based deployments, we connect to a cloud-based postgres instance. For GCP, the connection is established by use of Google's cloud SQL proxy (https://cloud.google.com/sql/docs/postgres/sql-proxy). This software allows the cloud-based VM to securely connect to the database instance and creates a socket on the VM. Django can then communicate with the database via this socket as if the database server were also located on the VM.

    
**The Cromwell server**

To run larger, more computationally demanding jobs we connect WebMEV to a remote Cromwell job scheduler which provides on-demand compute resources. When implemented as part of a cloud-based deployment, Cromwell resides on an independent VM. Job requests are sent from the WebMEV server to Cromwell's RESTful API. Upon receiving the necessary components of a job request (WDL scripts, JSON inputs), Cromwell orchestrates the provisioning of hardware to execute the job(s). After completion, Cromwell handles the destruction of these ephemeral resources and places any output files into storage buckets. WebMEV handles the querying of job status, relocation of result files, and any other WebMEV-specific business logic.