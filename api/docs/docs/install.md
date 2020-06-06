## Installation instructions

#### Dockerhub image

TODO

#### Local build

The application is packaged as a Docker for easier management of dependencies.  To build the Docker image yourself, you will need to have Docker installed locally.

To build the application, clone the repository locally:
```
git clone https://github.com/qbrc-cnap/mev-backend.git
```

Navigate into that cloned directory and build the Docker image with:
```
docker build -t <image name> .
```

To run the container, you will need to supply some environment variables for things like passwords and other sensitive information.  In the repository is a file named `env_vars.template.txt`.  Fill that in with the various usernames and passwords as you like.  In particular, if you are running a local development version, you will need to specify:
```
ENVIRONMENT=dev
```
Additionally, specify the same value (an email address) for both `DJANGO_SUPERUSER_EMAIL` and `DJANGO_SUPERUSER_USERNAME`.  This is because MEV uses emails as the unique usernames.
 
If you would like some "dummy" data to be entered into the database (e.g. for developing a front-end), you must also specify `POPULUATE_DB=yes` (case-sensitive!).  Any other values for this variable will skip the population of dummy data.

To run the container:
```
docker run -it --env-file <ENV VARS> -p8000:8000 <DOCKER IMAGE NAME> --bind 0.0.0.0:8000
```

Note the following:

- We bind port 8000 *inside* the container to 8000 *outside* the container.
- Due to the use of `ENTRYPOINT` in the Dockerfile, the commands following the image name (e.g. `--bind 0.0.0.0:8000` above) will be appended to the command:
```
gunicorn mev.wsgi:application
```

Therefore, for the example given above, the full command on startup would then be,
```
gunicorn mev.wsgi:application --bind 0.0.0.0:8000
```
which starts `gunicorn` and listens for connections on `0.0.0.0:8000`.  This allows one to access the API from outside the container. Note that additional gunicorn configuration parameters can be specified (see https://docs.gunicorn.org/en/latest/configure.html). 

At this point you may go to your browser and navigate to http://127.0.0.1:8000/api/.  You will need to login with the username (email) and password you gave in your file of environment variables.


