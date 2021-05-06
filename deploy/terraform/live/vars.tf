variable "environment" {
    description = ""
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
    default = "ubuntu-2004-focal-v20210325"
}

variable "api_os_image" {
    default = "ubuntu-2004-focal-v20210325"
}

variable "cromwell_bucket" {
  description = "Name of the bucket where Cromwell will place its files. Do NOT include the gs prefix."
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

variable "branch" {
  description = "The git branch to use"
  default = "deploy"
}

variable "domain" {
  description = "The domain where the API will be served from."
}

variable "managed_dns_zone" {
  description = "The name of the managed zone where DNS is handled. Short name only."
}

variable "db_user" {
}

variable "root_db_passwd" {
}

variable "db_passwd" {
}

variable "db_name" {
}

variable "db_port" {
    default = 5432
}

variable "repo" {
}

variable "django_secret" {
    
}

variable "frontend_domain" {
}

variable "django_superuser_passwd" {
}

variable "django_superuser_email" {
}

variable "mev_storage_bucket" {
  description = "Name of the bucket. No prefix"
}

variable "email_backend" {
  default = "GMAIL"
}

variable "from_email" {}

variable "gmail_access_token" {}
variable "gmail_refresh_token" {}
variable "gmail_client_id" {}
variable "gmail_client_secret" {}

variable "sentry_url" {}

variable "dockerhub_username" {}
variable "dockerhub_passwd" {}