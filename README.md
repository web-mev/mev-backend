# Note that due to Federal grant withdrawals related to Harvard University, this project is no longer maintained

# WebMEV RESTful API

A Django Rest Framework backend for the MEV web application.  See full documentation on concepts and usage at https://web-mev.github.io/mev-backend/

## Quick start for local development
Install [Git](https://git-scm.com/), [VirtualBox](https://www.virtualbox.org/), and [Vagrant](https://www.vagrantup.com/)
```shell
git clone https://github.com/web-mev/mev-backend.git
cd mev-backend
vagrant up
```
Open http://localhost:8080/api/ in a web browser

## Deployment to AWS

For instructions on deploying on AWS using Terraform, see the [README here](https://github.com/web-mev/mev-backend/blob/dev/deployment-aws/README.md)
