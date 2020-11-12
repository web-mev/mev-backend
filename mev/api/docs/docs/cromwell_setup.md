## Cromwell server setup

This section covers the setup of a second machine which will act as the Cromwell server.  This server is responsible for handling remote job submissions from WebMEV and performing all the orchestration of cloud-based resources (e.g. starting VMs, pulling data from storage buckets).

### Creating a new VM

Depending on your cloud platform, starting the new compute instance will be different. However, the instructions below were only run on a Debian distro. We make note of the following considerations:

- Documentation on the machine requirements is challenging to find on the Cromwell site, but we have had success using a machine with 2 vCPU and 8Gb RAM.

- Cromwell produces rather verbose logs, although these are only simple text files without a huge footprint. We have used 100Gb.

- You must expose port 8000 on this machine, which is the default port for Cromwell. Other ports can be configured, but we do not cover that here.

- We create a firewall rule which only allows requests originating from the WebMEV machine. For WebMEV, there is no need to expose Cromwell publicly.

### Installing and configuring Cromwell server

SSH into the Cromwell host.  Install the Java runtime environment, which we need to run Cromwell:
```
$ sudo -s
$ apt-get update
$ apt-get install -y default-jre
```

We also need Docker to be installed-- for ease of installation, we simply use a MySQL Docker container.  Of course you may wish to install MySQL directly on your Cromwell server, but that is not covered here.  We follow the instructions for installing Docker and then run:

```
docker run -p 3306:3306 --name mysql_container \
    -e MYSQL_ROOT_PASSWORD=<ROOT PASSWORD> \
    -e MYSQL_DATABASE=<DATABASE NAME> \
    -e MYSQL_USER=<DATABASE USER> \
    -e MYSQL_PASSWORD=<DATABASE USER PASSWORD> \ 
    -d mysql/mysql-server:5.7
```

Note that the `latest` image version ended up causing problems with Cromwell, so we used 5.7.  Also be sure to change the various usernames/passwords above.  


Now get the latest Cromwell JAR from the Broad Institute's Github (https://github.com/broadinstitute/cromwell/releases).  We keep the JAR under a new directory, `/opt/cromwell/`.

```
$ mkdir /opt/cromwell
$ wget https://github.com/broadinstitute/cromwell/releases/download/36/cromwell-36.jar -P /opt/cromwell/
```
Since we would like Cromwell to remain alive (and recover from failures), we place it under control of supervisor, which we need to install

```
$ apt-get install -y supervisor
```

We will also create a non-root user to run execute Cromwell:
```
$ adduser cromwell-runner
```

In addition, we need to create a folder for Cromwell to write logs.  By default it tries to write to `/cromwell-workflow-logs`.  so we must create a folder there and give ownership of that folder to the `cromwell-runner` user.  As root (which you should be):
```
$ mkdir /cromwell-workflow-logs
$ chown cromwell-runner:cromwell-runner /cromwell-workflow-logs
```

Create a conf file for supervisor at `/etc/supervisor/conf.d/cromwell.conf`: 

```
[program:cromwell_server]
command=/usr/bin/java -D<JAVA PROPERTIES> -jar /opt/cromwell/cromwell-<VERSION>.jar server
user=cromwell-runner

; Put process stdout output in this file
stdout_logfile=/var/log/cromwell/stdout.log

; Put process stderr output in this file
stderr_logfile=/var/log/cromwell/stderr.log

autostart=true
autorestart=true
stopsignal=QUIT
```

Note that you should change the path to the JAR file to match the version you have downloaded. Also take note of the template/dummy `-D<JAVA PROPERTIES>` flag at the start of the `command` parameter.  This provides arguments to the Java runtime environment (JRE).  This flag is not strictly required (and should be removed if no arguments are passed), but when running on a cloud platform, we typically use the `-D` flag to pass the path to a configuration file. That config file contains platform-specific parameters which dictate how Cromwell is to be run when using a specific cloud platform.  Details about these files are given below.

Prior to starting supervisor, the log directory needs to be created:
```
$ mkdir /var/log/cromwell
```

Then start supervisor:
```
$ supervisord
$ supervisorctl reread
$ supervisorctl update
```
Running `supervisorctl status` should show the `cromwell_server` process as `RUNNING` if all is well.  To test that the Cromwell server is up, you can check the log at `/var/log/cromwell/stdout.log`.  

To test that Cromwell is able to respond to your requests, you can log into the main application VM and initiate a request to one of the Cromwell API endpoints.  For instance, you can query the job status endpoint (here using a random, but valid UUID):

```
 $ curl -X GET http://<CROMWELL SERVER IP>:8000/api/workflows/v1/e442e52a-9de1-47f0-8b4f-e6e565008cf1/status
```

If the server is running, it will return a 404 (with the JSON below) since the random UUID will not be a job identifier that Cromwell is aware of:

```
{
    "status": "fail",
    "message": "Unrecognized workflow ID: e442e52a-9de1-47f0-8b4f-e6e565008cf1"
}
```

If you try this same request from a different machine (e.g. your local machine), the request should timeout if the firewall rule was applied correctly.

**GCP configuration**

As described above, for Cromwell to have access to GCP resources (e.g. to start VMs and access bucket storage), it needs to be started with a configuration file specific to GCP.  A template is provided at `cromwell/google.template.conf`.  Project-specific variables are encased in angle brackets "<", ">", and need to be completed before using with the Cromwell JAR.  Specifically, you need to fill-in the google project ID (the name, *not* the numeric project ID), and the location of an *existing* storage bucket where Cromwell will execute the workflows. Also note the `database` stanza, where you include database name, user, and password details; these should match the corresponding values you entered when starting the MySQL Docker container above.  

Once complete, save this file on the Cromwell server; below we chose to locate it at `/opt/cromwell/google.conf`.  The `command` in the supervisor config file above should then point at this config file, reading:
```
...
command=/usr/bin/java -Dconfig.file=/opt/cromwell/google.conf -jar /opt/cromwell/cromwell-<VERSION>.jar server
...
```