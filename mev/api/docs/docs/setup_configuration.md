## Configuration options and parameters

As described in the installation section, the WebMEV API depends on environment variables passed to the container using the `--env-file` argument.  Most variables defined in `env_vars.template.txt` should be appropriately commented, but we provide some additional instructions or commentary below.

### Email backends (`EMAIL_BACKEND_CHOICE`)

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

- Choose a Gmail account (or create one anew) from which you wish to send email notifications.  On your own machine (or wherever you can login to your Google account), go to the Google developers console ( https://console.developers.google.com  or https://console.cloud.google.com ) and head to "APIs & Services" and "Dashboard".  Click on "Enable APIs and Services", search for "Gmail", and enable the Gmail API. 

- Once that is enabled, go to the "Credentials" section under "APIs and Services".  Just as above, we will create a set of OAuth credentials.  Click on the "Create credentials" button and choose "OAuth Client ID".   Choose "Other" from the options and give these credentials a name.

- Once the credentials are created, download the JSON-format file when it prompts.

- Using that credential file, run the `helpers/exchange_gmail_credentials.py` script like:

```
python3 helpers/exchange_gmail_credentials.py -i <original_creds_path> -o <final_creds_path>
```
(Note that this script can be run from within the WebMEV Docker container, as it contains the appropriate Python packages.  If you are not using the application container, you can run the script as long as the `google-auth-oauthlib` library is installed-- https://pypi.org/project/google-auth-oauthlib/ )

The script will ask you to copy a link into your browser, which you can do on any machine where you can authenticate with Google.  That URL will ask you to choose/log-in to the Gmail account you will be using to send emails.  Finally, if successfully authenticated, it will provide you with a "code" which you will copy into your terminal.  Once complete, the script will write a new JSON-format file at the location specified with the `-o` argument.

- Using the values in that final JSON file, copy/paste those into the file of environment variables you will be submitting to the WebMEV container upon startup. *Be careful with these credentials as they give full access to the Gmail account in question!!*  

### Storage backends (`RESOURCE_STORAGE_BACKEND`)

Storage of user files can be either local (on the MEV server) or in some remote filesystem (such as in a Google storage bucket).  To abstract this, we have storage "backends" that control the behavior for each storage choice.

Options for storage backends can be found in the `api/storage_backends` folder.  To use a particular backend, we supply the "dotted" path for the class that implements the storage interface.  For example, to use the Google bucket storage backend, we would use `RESOURCE_STORAGE_BACKEND=api.storage_backends.google_cloud.GoogleBucketStorage` since the `GoogleBucketStorage` class is located in `api/storage_backends/google_cloud.py`.

Note that each storage backend may require additional environment variables to be set.  We enforce this by attempting an initial import of the storage backend class.  By convention, any configuration parameters required should at the "top-level" of the Python module/file.  This way, when we attempt the import while starting the application, any missing configuration variables will raise an exception.  This (hopefully) prevents errors in runtime due to incomplete/invalid configuration.
