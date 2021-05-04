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

# open the default port 8000
resource "google_compute_firewall" "cromwell_firewall" {
  name    = "cromwell-${var.environment}-firewall"
  network = google_compute_network.mev_api_network.name

  allow {
    protocol                 = "tcp"
    ports                    = ["8000"]
  }

  # source_tags = ["mev-api"]
  target_tags = ["cromwell-8000"]
}

# Allow SSH into that machine
resource "google_compute_firewall" "cromwell_ssh" {
  name    = "cromwell-${var.environment}-ssh"
  network = google_compute_network.mev_api_network.name

  allow {
    protocol                 = "tcp"
    ports                    = ["22"]
  }

  target_tags = ["basic-ssh"]
}

# Allow http into that machine
resource "google_compute_firewall" "cromwell_http" {
  name    = "cromwell-${var.environment}-http"
  network = google_compute_network.mev_api_network.name

  allow {
    protocol                 = "tcp"
    ports                    = ["8000"]
  }

  target_tags = ["cromwell-8000"]
}


resource "google_compute_instance" "cromwell" {
  name                    = "cromwell-${var.environment}"
  machine_type            = var.cromwell_machine_config.machine_type
  tags                    = ["cromwell-8000", "basic-ssh"]
  labels                  = {
                                "app" = "mev-api"
                                "environment" = var.environment
                            }

  metadata_startup_script = templatefile("cromwell_provision.sh", 
    { 
      project_id = var.project_id,
      cromwell_bucket = "gs://${var.cromwell_bucket}",
      cromwell_db_name = var.cromwell_db_name,
      cromwell_db_user = var.cromwell_db_user,
      cromwell_db_password = var.cromwell_db_password,
      branch = var.branch
    }
  )

  boot_disk {
    initialize_params {
      image = var.cromwell_os_image
      size = var.cromwell_machine_config.disk_size_gb
    }
  }

  network_interface {
    network = google_compute_network.mev_api_network.name
    access_config {
    }
  }
}
