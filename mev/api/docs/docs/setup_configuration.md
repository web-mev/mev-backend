## Configuration options and parameters

As described in the installation section, the WebMEV API depends on environment variables passed to the container using the `env_file` parameter in the docker-compose YAML file.  Most variables defined in `env_vars.template.txt` should be appropriately commented, but we provide some additional instructions or commentary below.


- `DJANGO_ALLOWED_HOSTS`: If you are deploying on a host that is not your own computer (such as on a cloud machine), supply the IP address or domain.

- `DJANGO_CORS_ORIGINS`: If you are using a front-end framework located on a different domain, you will need to add this to the comma-delimited list.  Otherwise you will get failures due to violoating same-origin policy.

- `CLOUD_PLATFORM`: Which cloud platform you are using. We don't allow "mixing" (e.g. using AWS' S3 bucket storage but deploying on a GCP compute instance). If you are deploying locally, then this can be left blank.

- `ENABLE_REMOTE_JOB_RUNNERS`: This flag controls whether we want to use the remote (e.g. Cromwell) job runners. Anything other than `"yes"` will disable (i.e. you will NOT be able to run remote jobs)

- `REMOTE_JOB_RUNNERS`: Check the list of implemented remote job runners specified in the `AVAILABLE_REMOTE_JOB_RUNNERS` variable in `mev/base_settings.py`

- `STORAGE_LOCATION`: This configures where user files are stored. If you only plan on using local Docker-based jobs, this can be set to `"local"`. *However,* if remote jobs are enabled, it *must* be set to `"remote"`. If we are using remote job runners, we enforce that we use remote (bucket-based) storage.

- `EMAIL_BACKEND_CHOICE`: Email-based registration depends on the ability to send emails, so a viable email backend must be chosen.  Refer to the settings file to see available options.  Currently only `GMAIL`. See [configuring email](#email) for more details.

- `SOCIAL_BACKENDS`: A list of social auth providers you wish to use.  Currently only Google.

 
If you would like some "dummy" data to be entered into the database (e.g. for developing a front-end), you must also specify `POPULUATE_DB=yes` (case-sensitive!).  Any other values for this variable will skip the population of dummy data.


### Email backends (`EMAIL_BACKEND_CHOICE`) <a name="email"></a>

Various operations like user registration and password changes require us to send users emails with encoded tokens to verify their email address and permit changes to their account.  Accordingly, WebMEV needs the ability to send emails.  We allow customization of this email backend through the `EMAIL_BACKEND_CHOICE` variable in `env_vars.template.txt`.

Certain cloud providers, such as GCP, place restrictions on outgoing emails to prevent abuse.  Per their documentation ( https://cloud.google.com/compute/docs/tutorials/sending-mail ), GCP recommends to use a third-party service such as SendGrid.  If you wish to use these, you will have to implement your own email backend per the interface described at the Django project: https://docs.djangoproject.com/en/3.0/topics/email/#defining-a-custom-email-backend

By default, we provide the following email backends:

**Console (`EMAIL_BACKEND_CHOICE=CONSOLE`)**

*Note: This backend is for development purposes only-- no emails are actually sent!*

If `EMAIL_BACKEND_CHOICE` is not set, WebMEV defaults to using Django's "console" backend, which simply prints the emails to stdout.  This is fine for development purposes where the tokens can be copy/pasted for live-testing, but is obviously not suitable for a production environment.

**Gmail (`EMAIL_BACKEND_CHOICE=GMAIL`)**

Alternatively, one can use the Gmail API to send emails from their personal or institution google account.  In addition to setting `EMAIL_BACKEND_CHOICE=GMAIL`, you will need to set the following additional variables:
```
GMAIL_ACCESS_TOKEN=
GMAIL_REFRESH_TOKEN=
GMAIL_CLIENT_ID=
GMAIL_CLIENT_SECRET=
```   

These variables are obtained after you have created appropriate credentials and performed an Oauth2-based exchange, which we describe.

*Steps:*

- Choose a Gmail account (or create a new account) from which you wish to send email notifications.  On your own machine (or wherever you can login to your Google account), go to the Google developers console ( https://console.developers.google.com  or https://console.cloud.google.com ) and head to "APIs & Services" and "Dashboard".  Click on "Enable APIs and Services", search for "Gmail", and enable the Gmail API. 

- Go to the "Credentials" section under "APIs and Services".  Just as above, we will create a set of OAuth credentials.  Click on the "Create credentials" button and choose "OAuth Client ID".   Choose "Other" from the options and give these credentials a name.

- Once the credentials are created, download the JSON-format file when it prompts.

- Using that credential file, run the `helpers/exchange_gmail_credentials.py` script like:

```
python3 helpers/exchange_gmail_credentials.py -i <original_creds_path> -o <final_creds_path>
```
(Note that this script can be run from within the WebMEV Docker container, as it contains the appropriate Python packages.  If you are not using the application container, you can run the script as long as the `google-auth-oauthlib` (https://pypi.org/project/google-auth-oauthlib/) library is installed.

The script will ask you to copy a link into your browser, which you can do on any machine where you can authenticate with Google.  That URL will ask you to choose/log-in to the Gmail account you will be using to send emails.  Finally, if successfully authenticated, it will provide you with a "code" which you will copy into your terminal.  Once complete, the script will write a new JSON-format file at the location specified with the `-o` argument.

- Using the values in that final JSON file, copy/paste those into the file of environment variables you will be submitting to the WebMEV container upon startup (`env_vars.template.txt`). *Be careful with these credentials as they give full access to the Gmail account in question!!*  

### Storage backends (`STORAGE_LOCATION`)

Storage of user files can be either local (on the WebMEV server) or in some remote filesystem (e.g. in a Google storage bucket).  To abstract this, we have storage "backends" that control the behavior for each storage choice and provide a common interface.

Implementations for storage backends can be found in the `api/storage_backends` folder. However, for ease, we limit the options for these backends depending on other configuration variables.

For instance, if the admin indicates that they want to run remote jobs (e.g. with Cromwell), we only allow  `STORAGE_LOCATION=remote`, as the job runner will require access to bucket storage. We anticipate that the job runner will be handling/processing large files and we want to keep all files in remote bucket-based storage instead of consuming disk space on the host machine.  Thus, one may only use `STORAGE_LOCATION=local` if they are only planning to use local Docker-based jobs.

Note that each storage backend may require additional environment variables to be set. For instance, if using the bucket-based backend, we naturally require the name of the bucket we will be using. Checking for these additional required environment variables is accomplished by attempting an initial import of the storage backend class during startup of the Django applicatoin.  By convention, any configuration parameters required should at the "top-level" of the Python module/file.  This way, when we attempt the import while starting the application, any missing configuration variables will raise an exception.  This (ideally) prevents errors in runtime due to incomplete/invalid configuration.

### Dockerhub integration

To enforce that the containers used in WebMEV are available for the purpose of reproducibility, we dynamically build and push Docker images to Dockerhub. Thus, we require that you specify your username and password so that the push capability works.

### Cromwell integration

If you are using the remote Cromwell job runner, we need to know the location (URL, IP address) and port of the Cromwell server. Furthermore, you need to specify the bucket associated with Cromwell. As a reminder, the configuration of the Cromwell server requires that you specify a bucket where it will store its files. We need to know the name of that bucket within WebMEV. See [Cromwell setup](cromwell_setup.md) for more details
