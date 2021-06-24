### To run WebMeV in a local development environment using Vagrant:

These steps assume you are at the "root" of the repository where the `Vagrantfile` lives.

- Copy the environment variables file, `vagrant/env.tmpl`, and fill the variables with appropriate values. Call this `vagrant/env.txt`

- Source that file (`source vagrant/env.txt`) to populate the environment variables

- Start vagrant: `vagrant up --provision`

- Once provisioning is complete, SSH into the VM: `vagrant ssh`

- Once in the VM, change to the host mount: `cd /vagrant`

- Since this is a new shell, we need those environment variables to be set again: Run `source vagrant/final_setup.sh vagrant/env.txt`

- Check if the supervisor daemon is running. If the machine was just provisioned, this is often the case. However, if you are resuming a VM that is already provisioned, it is likely NOT running. To check the supervisor daemon status, you must be root. Hence, run:

```
sudo -s
supervisorctl status
```
If it responds that there is no socket (e.g. `unix:///var/run/supervisor.sock no such file`), then start supervisor with:

```
supervisord -c /etc/supervisor/supervisord.conf
```

If you *did* have to start supervisor above, a status check (`supervisorctl status`) will reveal that you will need to start the individual processes. To start those, run:

```
supervisorctl start redis
supervisorctl start mev_celery_beat
supervisorctl start mev_celery_worker
```


**To start the application server:** 

To interact with the supervisord process, you need to be root (if you are not already), so run `sudo -s`

Then start gunicorn: `supervisorctl start gunicorn`

The application will be available at `localhost:8080/api/`


**To run unit tests:**
```
cd /vagrant/mev
python3 manage.py test 
```

