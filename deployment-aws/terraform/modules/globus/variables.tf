variable "app_client_secret" {
  description = "The corresponding secret for the Globus application"
  type        = string
}

variable "app_client_uuid" {
  description = "The UUID for the Globus application client"
  type        = string
}

variable "data_bucket" {
  description = "Name of the S3 bucket used for data transfers"
  type        = string
}

variable "endpoint_client_secret" {
  description = "The corresponding secret for the Globus endpoint client"
  type        = string
}

variable "endpoint_client_uuid" {
  description = "The UUID for the Globus endpoint client"
  type        = string
}

variable "endpoint_id" {
  description = "The endpoint UUID for the Globus shared collection."
  type        = string
}

variable "name_prefix" {
  description = "Prefix to use for resource name tags"
  type        = string
}

variable "secrets_bucket" {
  description = "Name of the S3 bucket used for secrets"
  type        = string
}

variable "secrets_prefix" {
  description = "S3 object key prefix used for secrets"
  type        = string
}

variable "subnet_id" {
  description = "ID of a public subnet where Globus server will be deployed"
  type        = string
}

variable "vpc_id" {
  description = "ID of the VPC where Globus server will be deployed"
  type        = string
}
