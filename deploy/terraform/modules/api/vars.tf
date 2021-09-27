variable "cromwell_ip" {
    description = "The IP of the Cromwell server"
}

variable "environment" {
    description = ""
    default = "dev"
}

variable "ssh_tag" {
    description = "Used to tag the VM instance to allow SSH connections"
}

variable "network"{
  description = "The GCP VPC"
}


variable "api_os_image" {
    description = ""
}

variable "api_machine_config" {
  type    = object({
                machine_type   = string
                disk_size_gb   = number
            })
}

variable "domain" {
  description = "The domain where the API will be served from."
}

variable "managed_dns_zone" {
  description = "The name of the managed zone where DNS is handled. Short name only."
}

variable "db_user" {
    description = "Username for the postgres database that will be used by WebMEV"
}

variable "root_db_passwd" {
    description = "Password for the postgres root user"
}

variable "db_passwd" {
  description = "Password for the postgres database that will be used by WebMEV"
}

variable "db_name" {
  description = "The name of the postgres database that will be used by WebMEV"
}

variable "db_port" {
  description = "The port on which the postgres database will listen."
  default = 5432
}

variable "db_host" {
    description = "The full name of the database server (cloud-based). Given as <project>:<region>:<db name>"
}

variable "commit_id" {
  description = "Identifies the specific commit which will be deployed."
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
  description = "The URL of the Sentry tracker. Include protocol, port"
}

variable "dockerhub_username" {
  description = "The username for your Dockerhub account"
}

variable "dockerhub_passwd" {
  description = "The password for your Dockerhub account"
}

variable "dockerhub_org" {
  description = "The organization of your Dockerhub user, which determines where any Docker images will be stored. If not supplied, images will be pushed to the user account."
  default = ""
}

variable "cromwell_bucket" {
  description = "Name of the bucket where Cromwell will place its files. Do NOT include the gs prefix."
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
  description = "A comma-delimited string dictating which remote job runners should be used. See the Django settings for acceptable values."
}

variable "storage_location" {
  description = "Where the data will be stored. One of remote or local"
}

variable "resource_name_prefix" {
  description = "Prefix added to resource names to avoid name collisions"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
}