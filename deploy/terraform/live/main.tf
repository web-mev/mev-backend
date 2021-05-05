terraform {
  required_version = "~> 0.14.8"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 3.60.0"
    }
  }
}

provider "google" {
  credentials = file(var.credentials_file)
  project     = var.project_id
  region      = var.region
  zone        = var.zone
}


resource "google_compute_network" "mev_api_network" {
    name           = "mev-${var.environment}-network"    
}

resource "google_compute_firewall" "mev_firewall" {
  name    = "webmev-ssh-firewall-${var.environment}"
  network = google_compute_network.mev_api_network.name

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  target_tags = ["allow-ssh-${var.environment}"]

}

module "cromwell" {
    source = "../modules/cromwell"
    project_id = var.project_id
    environment = var.environment
    network = google_compute_network.mev_api_network.name
    cromwell_machine_config = var.cromwell_machine_config
    cromwell_os_image = var.cromwell_os_image
    cromwell_bucket = var.cromwell_bucket
    cromwell_db_name = var.cromwell_db_name
    cromwell_db_user = var.cromwell_db_user
    cromwell_db_password = var.cromwell_db_password
    branch = var.branch
    ssh_tag = "allow-ssh-${var.environment}"
}

module "api" {
    source = "../modules/api"
    network = google_compute_network.mev_api_network.name
    environment = var.environment
    ssh_tag = "allow-ssh-${var.environment}"
    cromwell_ip = module.cromwell.cromwell_ip
    api_machine_config = var.api_machine_config
    api_os_image = var.api_os_image
    domain = var.domain
    managed_dns_zone = var.managed_dns_zone
}
