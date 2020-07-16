## Installation instructions

#### Dockerhub image

TODO

#### Local build

The application is packaged as a series of Docker images for easier management of dependencies.  The collective behavior and interdependencies is managed by `docker-compose`.  To build the application image yourself, you will need to have Docker and docker-compose installed locally.

To build the application, clone the repository locally:
```
git clone https://github.com/web-mev/mev-backend.git
```

To run the container, you will need to supply some environment variables for things like passwords and other sensitive information.  In the root of the repository is a file named `env_vars.template.txt`.  Fill that in with the various usernames and passwords as you like.  Each variable has a description to help.  In particular, note the following:

- `DJANGO_ALLOWED_HOSTS`: If you are deploying on a host that is not your own computer (e.g. on a cloud machine), supply the IP address or domain.
- `DJANGO_CORS_ORIGINS`: If you are using a front-end framework located on a different domain, you will need to add this to the comma-delimited list.  Otherwise you will get failures due to violoating same-origin policy.
- `RESOURCE_STORAGE_BACKEND`: This configures where user files are stored.  By default, it is local.  Other storage backends may be configured (i.e. for cloud bucket-based storage).  Given as a "dotted" path to the storage class implementation.
- `EMAIL_BACKEND_CHOICE`: Email-based registration depends on the ability to send emails, so a viable email backend must be chosen.  Refer to the settings file to see available options.  Currently only `GMAIL`.
- `SOCIAL_BACKENDS`: A list of social auth providers you wish to use.  Currently only Google.

 
If you would like some "dummy" data to be entered into the database (e.g. for developing a front-end), you must also specify `POPULUATE_DB=yes` (case-sensitive!).  Any other values for this variable will skip the population of dummy data.

For more information on configuration, see [Configuration](resource_metadata.md)

**To start the application in *development* mode:**

In development mode, the application server (gunicorn) does not start automatically as the container starts.  Rather, all the containers are started but the application container (`api`) remains idle.  This allows us to mount a local directory where we can dynamically edit the code and immediately see changes.  Note that the Django `DEBUG` argument is set to `True` in this case, so be mindful of using development mode if the server is exposed to the public.

In the root of the repository (where the `docker-compose.yml` file resides) run:
```
docker-compose up -d --build
```
This builds all the containers and runs in "detached" mode.  By default, `docker-compose` will look for the `docker-compose.yml` file which, by design, puts us in *development* mode.  The current directory on the host machine will be mounted at `/workspace` inside the `api` container.

Next, enter the container with:
```
docker-compose exec api /bin/bash
```
You may optionally choose to add the `-u 0` flag which logs you into the `api` container as root.

Once inside, run the following:
```
cd /workspace/mev
source startup.sh
```
This will run some database migrations and other preliminaries, but will **not** actually start the gunicorn application server.  To do that, you must then run:
```
cd /workspace/mev
gunicorn mev.wsgi:application --bind 0.0.0.0:8000
```
(note the `cd` at the top since the `startup.sh` script ends up moving you into the `/www` directory).  The `bind` argument should have the port set to 8000 as this is how the NGINX container communicates over the internal docker-compose network.

Following all that, the application should be running on port 8081 (e.g. http://127.0.0.1:8081/api/)


If you are interested, note that additional gunicorn configuration parameters can be specified (see https://docs.gunicorn.org/en/latest/configure.html). 

By stopping the gunicorn server (Ctrl+C), you can make local edits to your code (again, connected *into* the container via the volume mount) and immediately restart the server to see the changes.  The unit test suite can also be run in this manner with
```
python3 /workspace/mev/manage.py test
```

**To start the application in *production* mode:**

In production mode, the application server *will* be started following the usual startup steps contained in `startup.sh`.

In the root of the repository (where the `docker-compose.prod.yml` file resides) run:
```
docker-compose -f docker-compose.prod.yml up -d --build
```

This should start everything up.  On occasion, if you are very quick to navigate to the site, NGINX will issue a 502 bad gateway error.  However, a refresh should open the site correctly.  

In production mode, Django debugging is turned off, so any errors will be reported as generic 500 server errors without any corresponding details.

**Stopping the application**

To shut down the application (in verbose mode), run
```
docker-compose down -v
```
