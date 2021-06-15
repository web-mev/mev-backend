### To run WebMeV in a local development environment using Vagrant:

These steps assume you are at the "root" of the repository where the `Vagrantfile` lives.

- Copy the environment variables file, `vagrant/env.tmpl`, and fill the variables with appropriate values. Call this `vagrant/env.txt`

- Source that file (`source vagrant/env.txt`) to populate the environment variables

- Start vagrant: `vagrant up --provision`

- Once provisioning is complete, SSH into the VM: `vagrant ssh`

- Once in the VM, change to the host mount: `cd /vagrant`

- Since this is a new shell, we need those environment variables to be set again: Run `source vagrant/final_setup.sh vagrant/env.txt`

**To start the application server:** 

To interact with the supervisord process, you need to be root, so run `sudo -s`

Then start gunicorn: `supervisorctl start gunicorn`

The application will be available at `localhost:8080/api/`

**To run unit tests:**

```
cd /vagrant/mev
python3 manage.py test 
```

