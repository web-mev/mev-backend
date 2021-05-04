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

variable "cromwell_os_image" {
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