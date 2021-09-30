variable "environment" {
    description = "Sets the django settings module. dev or prod"
    default = "dev"
}

variable "project_id" {
  description = "GCP project ID"
}

variable "credentials_file" {
  description = "Path to JSON file with GCP service account key"
}

variable "region" {
  default = "us-east4"
}

variable "zone" {
  default = "us-east4-c"
}

variable "cromwell_machine_config" {
  type    = object({
                machine_type   = string
                disk_size_gb   = number
            })
}

variable "api_machine_config" {
  type    = object({
                machine_type   = string
                disk_size_gb   = number
            })
}

variable "cromwell_os_image" {
  default = "ubuntu-2004-focal-v20210927"
}

variable "api_os_image" {
  default = "ubuntu-2004-focal-v20210927"
}

variable "cromwell_db_name" {
  description = "The name of the database."
  type        = string
  sensitive   = true
}

variable "cromwell_db_user" {
  description = "The database user."
  type        = string
  sensitive   = true
}

variable "cromwell_db_password" {
  description = "Password for the database"
  type        = string
  sensitive   = true
}

variable "domain" {
  description = "The domain where the API will be served from."
}

variable "managed_dns_zone" {
  description = "The name of the managed zone where DNS is handled. Short name only."
}

variable "db_user" {
  default = "mevdbuser"
  description = "Username for the postgres database that will be used by WebMEV"
}

variable "root_db_passwd" {
    description = "Password for the postgres root user"
}

variable "db_passwd" {
  description = "Password for the postgres database that will be used by WebMEV"
}

variable "db_name" {
  default     = "mevdb"
  description = "The name of the postgres database that will be used by WebMEV"
}

variable "db_port" {
  description = "The port on which the postgres database will listen."
  default = 5432
}

variable "commit_id" {
  description = "The github commit to use for deployment."
}

variable "django_secret" {
    description = "The Django secret key"
}

variable "frontend_domain" {
  description = "The primary frontend domain this API will serve. Do NOT include protocol"
}

variable "django_superuser_passwd" {
  description = "Password for the Django admin/superuser"
}

variable "django_superuser_email" {
  description = "The email of the Django admin"
}

variable "storage_location" {
  description = "Where the data will be stored. One of remote or local"
}

variable "email_backend" {
  description = "The backend email service we use to send emails."
  default = "GMAIL"
}

variable "from_email" {
  description = "When registration emails are sent, this will be used for the sender. Format like: Name <account@domain>"
}

variable "gmail_access_token" {
  description = "For using Gmail API to send messages"
}

variable "gmail_refresh_token" {
  description = "For using Gmail API to send messages"
}

variable "gmail_client_id" {
  description = "For using Gmail API to send messages"
}

variable "gmail_client_secret" {
  description = "For using Gmail API to send messages"
}

variable "sentry_url" {
  default     = ""
  description = "The URL of the Sentry tracker. Include protocol, port"
}

variable "dockerhub_username" {
  default     = "mev"
  description = "The username for your Dockerhub account"
}

variable "dockerhub_passwd" {
  default     = "pass"
  description = "The password for your Dockerhub account"
}

variable "dockerhub_org" {
  default     = "org"
  description = "The organization of your Dockerhub user, which determines where any Docker images will be stored. If not supplied, images will be pushed to the user account."
}

variable "other_cors_origins" {
  description = "Additional frontend origins which should be permitted. Can be used so that local frontend development can communicate with the backend. This is in addition to the primary frontend domain this app will serve. Provided as a comma-delimited string"
}

variable "service_account_email" {
  description = "The email-like identifier of the service account attached to the VM instance. Must have adequate permissions."
}

variable "ssl_cert" {
  description = "The identifiers for the SSL certificate to use for the load balancer."
}

variable "enable_remote_job_runners" {
  description = "Whether we will be using the remote job runners like Cromwell"
}

variable "remote_job_runners" {
  default     = "CROMWELL"
  description = "A comma-delimited string dictating which remote job runners should be used. See the Django settings for acceptable values."
  type        = string
}
