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