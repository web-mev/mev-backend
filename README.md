# WebMEV RESTful API

A Django Rest Framework backend for the MEV web application.  See documentation at https://web-mev.github.io/mev-backend/

## Quick start
1. Install [Git](https://git-scm.com/), [VirtualBox](https://www.virtualbox.org/), and [Vagrant](https://www.vagrantup.com/)
1. `git clone https://github.com/web-mev/mev-backend.git`
1. Fill out the `vagrant/env.tmpl` with appropriate variables. Best to copy that (e.g. to `vagrant/env.txt`) so you don't accidentally commit any changes to that template file.
1. Source those environment variables: `source vagrant/env.txt` so they are now in your shell session.
1. Start and provision: `vagrant up`
