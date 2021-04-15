terraform {
  required_version = "~> 0.15.0"
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
  name    = "mev-${var.environment}-firewall"
  network = google_compute_network.mev_api_network.name

  allow {
    protocol                 = "tcp"
    ports                    = ["22", "80", "443"]
  }

  target_tags = ["web"]
}


resource "google_compute_firewall" "cromwell_firewall" {
  name    = "cromwell-${var.environment}-firewall"
  network = google_compute_network.mev_api_network.name

  allow {
    protocol                 = "tcp"
    ports                    = ["8000"]
  }

  source_tags = ["mev-api"]
  target_tags = ["cromwell-8000"]
}

resource "google_compute_firewall" "cromwell_ssh" {
  name    = "cromwell-${var.environment}-ssh"
  network = google_compute_network.mev_api_network.name

  allow {
    protocol                 = "tcp"
    ports                    = ["22"]
  }

  target_tags = ["basic-ssh"]
}


resource "google_compute_address" "mev-static-ip" {
  name = "mev-${var.environment}-static-address"
}


resource "google_compute_address" "cromwell-static-ip" {
  name = "cromwell-${var.environment}-static-address"
}


resource "google_compute_instance" "mev_api" {
  name                    = "test-mev-api-${var.environment}"
  machine_type            = var.api_machine_config.machine_type
  tags                    = ["web", "mev-api"]
  labels                  = {
                                "app" = "mev-api"
                                "environment" = var.environment
                            }

  #metadata_startup_script = file("api_provision.sh")

  boot_disk {
    initialize_params {
      image = var.api_os_image
      size = var.api_machine_config.disk_size_gb
    }
  }

  network_interface {
    network = google_compute_network.mev_api_network.name
    access_config {
      nat_ip = google_compute_address.mev-static-ip.address
    }
  }
}

resource "google_compute_instance" "cromwell" {
  name                    = "cromwell-${var.environment}"
  machine_type            = var.cromwell_machine_config.machine_type
  tags                    = ["cromwell-8000", "basic-ssh"]
  labels                  = {
                                "app" = "mev-api"
                                "environment" = var.environment
                            }

  metadata_startup_script = templatefile("bootstrap.tpl")

  boot_disk {
    initialize_params {
      image = var.cromwell_os_image
      size = var.cromwell_machine_config.disk_size_gb
    }
  }

  network_interface {
    network = google_compute_network.mev_api_network.name
    access_config {
      nat_ip = google_compute_address.cromwell-static-ip.address
    }
  }
}
