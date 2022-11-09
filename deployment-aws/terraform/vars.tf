variable "additional_cors_origins" {
  description = "Origins (including protocol and port) to include, in addition to the frontend_domain var."
  type        = string
  default     = ""
}

variable "admin_email_csv" {
  description = "A comma-delimited string of administrator emails"
  type        = string
}

variable "backend_domain" {
  description = "The domain where the API will be served from"
  type        = string
}

variable "container_registry" {
  description = "The Docker container registry you wish to use."
  type        = string
  default     = "github"
}

variable "data_volume_snapshot_id" {
  description = "Snapshot ID for the data volume. Used to persist data between deployments."
  default     = null
}

variable "django_settings_module" {
  description = "Settings module for the Django app"
  type        = string
  default     = "mev.settings_production"
}

variable "django_superuser_email" {
  description = "Email address to use as username for Django Admin"
  type        = string
}

variable "enable_remote_job_runners" {
  description = "Whether to use remote job runners like Cromwell"
  type        = string
  default     = "no"
}

variable "from_email" {
  description = "Used for the sender in registration emails. Format: Name <account@domain>"
  type        = string
}

variable "frontend_domain" {
  description = "The primary frontend domain this API will serve, do NOT include protocol"
  type        = string
}

variable "git_commit" {
  description = "Git repo code commit or branch name"
  type        = string
  default     = ""
}

variable "sentry_url" {
  description = "The URL of the Sentry tracker. Include protocol, port"
  type        = string
  default     = ""
}

variable "ssh_key_pair_name" {
  description = "SSH key pair name for API and Cromwell servers"
  type        = string
}

variable "storage_location" {
  description = "Where the data will be stored. One of remote or local"
  type        = string
  default     = "remote"
}

variable database_superuser_password {
  description = "Root password for database"
  type        = string
  sensitive   = true
}

variable database_password {
  description = "Password for mev database user"
  type        = string
  sensitive   = true
}

variable django_superuser_password {
  description = "Django superuser password"
  type        = string
  sensitive   = true
}

variable database_snapshot {
  description = "RDS snapshot ID"
  default = null
}
