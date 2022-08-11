variable "backend_domain" {
  description = "The domain where the API will be served from"
  type        = string
}

variable "frontend_domain" {
  description = "The primary frontend domain this API will serve, do NOT include protocol"
  type        = string
}

variable "git_commit" {
  description = "Git repo code commit or branch name"
  type        = string
  default     = "main"
}

variable "ssh_key_pair_name" {
  description = "SSH key pair name for API and Cromwell servers"
  type        = string
}