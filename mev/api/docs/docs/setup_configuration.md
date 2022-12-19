## Configuration options and parameters

As described in the installation section, the WebMeV API depends on environment variables to configure the application.

For local development with Vagrant, this may require setting some environment variables before running `vagrant up`. See `Vagrantfile` for details. In most cases, you do not need to modify anything or set environment variables. 

For a cloud-based deployment with terraform, you will need to create a `terraform.tfvars` file and enter the config parameters. See `deployment-aws/terraform/README.md` for details.

**Comments about configuration parameters:**

While most variables are sane default, note the following:

- `admin_email_csv`: This a comma-delimited string of the emails for administrators. Note that this does *not* create Django superusers, but rather provides a set of email addresses who will receive notifications (about errors, feedback, etc.)

- `enable_remote_job_runners`: The value "yes" enables the remote job runners like Cromwell. If any other value, then we will not allow remote jobs to be executed, which limits the types of analyses that can be run.

- `frontend_domain`: This is not strictly necessary, but will allow a frontend application located on another domain to interact with the API. Otherwise, Django will reject the request due to same-origin CORS policies. Do NOT include protocol.

- `additional_cors_origins`: This will allow additional frontend applications to connect. For instance, if you would like your local development frontend (accessible at localhost:4200) to connect to this deployment, you can add "http://localhost:4200". This is a comma-delimited string, so you can have multiple values. Be sure to include the http protocol, as shown.

- `storage_location`: This is either "remote" or "local". Using "remote" makes use of remote bucket storage. The "local" setting stores files on the server, which can be inappropriate for working with larger files since it requires larger hard disk space. **For cloud deployments, just set this to "remote".**

- `from_email`: We uses AWS simple email service (SES) to send emails. This sets to "from" field in the emails. It's helpful to set this to something like `"WebMEV <noreply@mail.webmev.tm4.org>"` so that users will know not to reply directly to the email.

- `sentry_url`: Only necessary to use if you are using a Sentry issue-tracker. If not using Sentry, then you can just leave this as an empty string.


### Email backends<a name="email"></a>

The "dev" settings (`mev/settings_dev.py`) use the default "console" email backend. This means that for development purposes, no emails will be sent. If you are deploying into a cloud environment, but want that enabled, alter that file OR just simply declare your dev environment as production. There's nothing particularly special about the "production" designation. It's effectively only production if it's properly associated with our "live" URL.

The "production" email uses AWS SES. Terraform will create an IAM user with appropriate permissions and the user/host/etc will automatically be linked up with the Django application during the provisioning.



### About storage backends

Storage of user files can be either local (on the WebMEV server) or in some remote filesystem (e.g. in an AWS S3 storage bucket).  To abstract this, we use the `django-storages` library for a common interface. For cloud deployments, we always use the "remote" setting, which corresponds to S3 storage. This setting is also required if you are planning to use the Cromwell (or other) remote job runner. Since Cromwell needs access to the files, we must be using bucket storage (barring some other, more complex setup).