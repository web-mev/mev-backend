variable "cromwell_ip" {
    description = "The IP of the Cromwell server"
}

variable "environment" {
    description = ""
    default = "dev"
}

variable "ssh_tag" {

}

variable "network"{
  
}


variable "api_os_image" {

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

variable "db_host" {
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
}

variable "email_backend" {
    default = "GMAIL"
}

variable "from_email" {}

variable "gmail_access_token" {}
variable "gmail_refresh_token" {}
variable "gmail_client_id" {}
variable "gmail_client_secret" {}

variable "sentry_url" {
}

variable "dockerhub_username" {}
variable "dockerhub_passwd" {}

variable "cromwell_bucket" {}

variable "branch" {}