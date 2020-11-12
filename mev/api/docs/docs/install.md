## Installation instructions

In its most common configuration, the WebMEV backend will consist of the application itself (the WebMEV application cluster, described below) and a remote job runner (typically Cromwell). The remote job runner is optional, but will allow you to easily integrate large, resource-intensive workflows such as alignments.

Below, we describe how to start and configure each component of a fully-featured WebMEV installation.

### Preliminaries

WebMEV was built to be a cloud-native application and assumes you will typically be operating on one of the supported cloud platform providers. However, use of a commercial cloud platform is not strictly necessary if you are only interested in using WebMEV's local Docker-based job runner.

If you are using a commercial cloud provider, we assume you are familiar with basic cloud-management operations such as creating storage buckets and starting/stopping compute instances. When applicable, we will highlight provider-specific differences necessary for setup/configuration of WebMEV.