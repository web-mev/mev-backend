## Installation instructions

The WebMEV backend consists of two virtual machines: the WebMEV web application itself and a remote job runner (Cromwell). The remote job runner is technically optional, but will allow you to easily integrate large, resource-intensive workflows such as alignments. We do not discuss custom deployments where the Cromwell server is omitted.


### Preliminaries

WebMEV was built to be a cloud-native application and assumes you will typically be operating on one of the supported cloud platform providers (currently only GCP). However, use of a commercial cloud platform is not strictly necessary if you are only interested in using WebMEV's local Docker-based job runner which permits jobs with relatively small computational requirements. For such a use-case, the local Vagrant-based environment is sufficient.

If you are using a commercial cloud provider, we assume you are familiar with basic cloud-management operations such as creating storage buckets and starting/stopping compute instances. When applicable, we will highlight provider-specific differences necessary for setup/configuration of WebMEV.