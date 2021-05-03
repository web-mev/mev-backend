variable "project_id" {
  description = "GCP project ID"
}


variable "credentials_file" {
  description = "Path to JSON file with GCP service account key"
}


variable "environment" {
    description = "The application environment- dev or prod."

    validation {
        condition = contains(["dev", "prod"], var.environment)
        error_message = "Invalid option for environment. Choose from either dev or prod."
    }
}


variable "api_machine_config" {
  type    = object({
                machine_type   = string
                disk_size_gb   = number
            })
}


variable "cromwell_machine_config" {
  type    = object({
                machine_type   = string
                disk_size_gb   = number
            })
}


variable "api_os_image" {
    default = "ubuntu-2004-focal-v20210325"
}


variable "cromwell_os_image" {
    default = "ubuntu-2004-focal-v20210325"
}


variable "region" {
  default = "us-east4"
}


variable "zone" {
  default = "us-east4-c"
}

variable "git_branch" {
  default     = "master"
  description = "Git repository branch to use for provisioning"
  type        = string
}

variable "managed_dns_zone" {
  description = "The existing managed DNS zone to which we will add a record."
  type        = string
}
