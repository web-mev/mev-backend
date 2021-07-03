## Configuration options and parameters

As described in the installation section, the WebMeV API depends on environment variables to configure the application.

For local development with Vagrant, this requires copying `vagrant/env.tmpl` to `vagrant/env.txt` and filling in the relevant variables. Each environment variable is commented with detailed explanations and you should consult that file for their interpretation. 

For a cloud-based deployment with terraform, you similarly need to copy the `config.tfvars.template` file to `terraform.tfvars` and enter the config parameters. For the most part, these variables are similar to the local deployment, but we make some detailed notes/comments below.

**Comments about configuration parameters:**

- `project_id`: This is the "string" name of the Google project, not the numerical ID.

- `credentials_file`: This is the name of the JSON-format file containing your service account credentials. See the section on setup to learn about where and how to obtain this file. This is assumed to reside in the `deploy/terraform/live` folder so your "main" `terraform.tfvars` file can reference it easily.

- `enable_remote_job_runners`: The value "yes" enables the remote job runners like Cromwell. If any other value, then we will not allow remote jobs to be executed, which limits the types of analyses that can be run.

- `cromwell_bucket`: The name (no `gs://` prefix!) of the storage bucket used by Cromwell. Ideally, this is in the same region/zone you are deploying in.

- `cromwell_db_*`: Database params, so make these appropriately secure.

- `service_account_email`: The full, email-like name for the service account you created for installation. See instructions there. Something like "abc123@myproject.iam.gserviceaccount.com".

- `managed_dns_zone`: As part of the deployment, we have terraform add DNS records which will point at the IP address of the public-facing load balancer. Hence, you must already have Google Cloud DNS as your nameserver for your domain. As mentioned in setup, deviations from this expectation are not covered and will require customization of your terraform `main.tf` script(s).

- `ssl_cert`: As described in the setup section, you will need to provision a SSL certificate to serve HTTPS. This certificate will be added to your load balancer. It is given as a "resource string", so it will be something like: `projects/<GCP PROJECT>/global/sslCertificates/<CERTIFICATE NAME>`.

- `domain`: The domain where your API will be accessed. We add a DNS record for this domain which points at the IP address of the load balancer.

- `frontend_domain`: This is not strictly necessary, but will allow a frontend application located on another domain to interact with the API. Otherwise, Django will reject the request due to same-origin CORS policies.

- `other_cors_origins`: This will allow additional frontend applications to connect. For instance, if you would like your local development frontend (accessible at localhost:4200) to connect to this deployment, you can add "http://localhost:4200". This is a comma-delimited string, so you can have multiple values. Be sure to include the http protocol, as shown.

- `mev_storage_bucket`: The name (no `gs://` prefix!) of the storage bucket used by WebMeV. This is where user's files are stored. Ideally, this is in the same region/zone you are deploying in.

- `storage_location`: This is either "remote" or "local". Using "remote" makes use of the Google storage bucket named above. The "local" setting stores files on the server, which can be inappropriate for working with larger files since it requires larger hard disk space. **For cloud deployments, just set this to "remote".**

- `from_email`: Since we are using the Gmail API, we can use a Google group-associated email send messages. Thus, if you are using the Gmail account of "user@gmail.com" who is associated with the "mygroup@gmail.com" address, then you can set this to "Some group <mygroup@gmail.com>" so that emails are sent on behalf of that group. This allows emails to appear to be sent from non-personal Gmail accounts. *Specify as a format like `"Some name <some@email.com>"`*

- `gmail_*`: These are the authentication parameters obtained by [performing an authentication flow with Gmail](#email). 

- `sentry_url`: Only necessary to use if you are using a Sentry issue-tracker. If not using Sentry, then you can just leave this as an empty string.

- `dockerhub_username`, `dockerhub_passwd`: These parameters are used to set your username and password for interacting with your Dockerhub account. This allows us to dynamically create Docker images and push them to the Dockerhub registry so that they are accessible and users can replicate their analyses.

- `dockerhub_org`: An organization-level account for Dockerhub. Your individual user must be associated with this organization. *If you do not have one or do not wish to use a Dockerhub organization, simply set this to your Dockerhub username*.

### Email backends (`EMAIL_BACKEND_CHOICE`) <a name="email"></a>

Various operations like user registration and password changes require us to send users emails with encoded tokens to verify their email address and permit changes to their account.  Accordingly, WebMEV needs the ability to send emails.  We allow customization of this email backend through the `EMAIL_BACKEND_CHOICE` Django setting. The value for that comes from the `EMAIL_BACKEND_CHOICE` environment variable for local dev and from the `email_backend` setting in `terraform.tfvars`. 

Certain cloud providers, such as GCP, place restrictions on outgoing emails to prevent abuse.  Per their documentation ( https://cloud.google.com/compute/docs/tutorials/sending-mail ), GCP recommends to use a third-party service such as SendGrid.  If you wish to use these, you will have to implement your own email backend per the interface described at the Django project: https://docs.djangoproject.com/en/3.0/topics/email/#defining-a-custom-email-backend

By default, we provide the following email backends. **Currently, the only real/outgoing mail backend is Gmail.**

**Console (`EMAIL_BACKEND_CHOICE=CONSOLE`)**

*Note: This backend is for development purposes only-- no emails are actually sent!*

If `EMAIL_BACKEND_CHOICE` is not set, WebMEV defaults to using Django's "console" backend, which simply prints the emails to stdout.  This is fine for development purposes where the tokens can be copy/pasted for live-testing, but is obviously not suitable for a production environment.

**Gmail (`EMAIL_BACKEND_CHOICE=GMAIL`)**

Alternatively, one can use the Gmail API to send emails from their personal or institution google account. **As mentioned, this is the only setting that allows actual email to be sent!** To use this email backend, you will need to perform an OAuth2 authentication flow to obtain the proper credentials: 

*Steps:*

- Choose a Gmail account (or create a new account) from which you wish to send email notifications.  On your own machine (or wherever you can login to your Google account), go to the Google developers console ( https://console.developers.google.com  or https://console.cloud.google.com ) and head to "APIs & Services" and "Dashboard".  Click on "Enable APIs and Services", search for "Gmail", and enable the Gmail API. 

- Go to the "Credentials" section under "APIs and Services".  Just as above, we will create a set of OAuth credentials.  Click on the "Create credentials" button and choose "OAuth Client ID".   Choose "Other" from the options and give these credentials a name.

- Once the credentials are created, download the JSON-format file when it prompts.

- Using that credential file, run the `helpers/exchange_gmail_credentials.py` script like:

```
python3 helpers/exchange_gmail_credentials.py -i <original_creds_path> -o <final_creds_path>
```
(Note that this script can be run from within the WebMeV local VM, as it contains the appropriate Python packages.  If you are not using the application container, you can run the script as long as the `google-auth-oauthlib` (https://pypi.org/project/google-auth-oauthlib/) library is installed.

The script will ask you to copy a link into your browser, which you can do on any machine where you can authenticate with Google.  That URL will ask you to choose/log-in to the Gmail account you will be using to send emails.  Finally, if successfully authenticated, it will provide you with a "code" which you will copy into your terminal.  Once complete, the script will write a new JSON-format file at the location specified with the `-o` argument.

- Using that final JSON file, you can fill in the *four* variables contained in either your `vagrant/env.txt` for local dev or your `deploy/terraform/live/terraform.tfvars` for a cloud deployment.  *Be careful with these credentials as they give full access to the Gmail account in question!!*  

### About storage backends

Storage of user files can be either local (on the WebMEV server) or in some remote filesystem (e.g. in a Google storage bucket).  To abstract this, we have storage "backends" that control the behavior for each storage choice and provide a common interface.

Implementations for storage backends can be found in the `api/storage_backends` folder. However, for ease, we limit the options for these backends depending on other configuration variables.

For instance, if the admin indicates that they want to run remote jobs (e.g. with Cromwell), we only allow remote storage (`storage_location = "remote"` in `terraform.tfvars`), as the job runner will require access to bucket storage. We anticipate that the job runner will be handling/processing large files and we want to keep all files in remote bucket-based storage instead of consuming disk space on the host machine.  Thus, one may only use `storage_location = "local"` if they are only planning to use local Docker-based jobs.

Note that each storage backend may require additional environment variables to be set. For instance, if using the bucket-based backend, we naturally require the name of the bucket we will be using (e.g. `mev_bucket_name` for GCP). Checking for these additional required environment variables is accomplished by attempting an initial import of the storage backend class during startup of the Django applicatoin.  By convention, any configuration parameters required should at the "top-level" of the Python module/file.  This way, when we attempt the import while starting the application, any missing configuration variables will raise an exception.  This (ideally) prevents errors in runtime due to incomplete/invalid configuration.
