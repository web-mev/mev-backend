# WebMEV RESTful API

A Django Rest Framework backend for the MEV web application.  See documentation at https://web-mev.github.io/mev-backend/

## Quick start
1. Install [Git](https://git-scm.com/), [VirtualBox](https://www.virtualbox.org/), and [Vagrant](https://www.vagrantup.com/)
1. `git clone https://github.com/web-mev/mev-backend.git`
1. Copy `vagrant/env.tmpl` to `vagrant/env.txt`
1. Edit `vagrant/env.txt` to provide values for the following variables:
   * DB_NAME, DB_USER, DB_PASSWD, ROOT_DB_PASSWD
   * RESTORE_FROM_BACKUP
   * DOCKERHUB_USERNAME, DOCKERHUB_PASSWORD, DOCKERHUB_ORG
   * DJANGO_SECRET_KEY
1. Start and configure the VM: `vagrant up`
