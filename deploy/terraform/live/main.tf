terraform {
  required_version = "~> 1.0.4"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 3.60.0"
    }
    external = {
      source  = "hashicorp/external"
      version = "~> 2.1.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.1.0"
    }
  }
}

provider "google" {
  credentials = file(var.credentials_file)
  project     = var.project_id
  region      = var.region
  zone        = var.zone
}

data "external" "git" {
  program = ["/bin/bash", "-c", "echo '{\"branch\": \"'$(git branch --show-current)'\"}'"]
}

resource "google_compute_network" "mev_api_network" {
    name           = "webmev-backend-${terraform.workspace}-network"    
}

resource "google_compute_firewall" "mev_firewall" {
  name    = "webmev-backend-ssh-firewall-${terraform.workspace}"
  network = google_compute_network.mev_api_network.name

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  target_tags = ["webmev-backend-allow-ssh-${terraform.workspace}"]

}

module "cromwell" {
    source = "../modules/cromwell"
    project_id = var.project_id
    environment = terraform.workspace
    network = google_compute_network.mev_api_network.name
    cromwell_machine_config = var.cromwell_machine_config
    cromwell_os_image = var.cromwell_os_image
    cromwell_db_name = var.cromwell_db_name
    cromwell_db_user = var.cromwell_db_user
    cromwell_db_password = var.cromwell_db_password
    commit_id = var.commit_id
    ssh_tag = "webmev-backend-allow-ssh-${terraform.workspace}"
    service_account_email = var.service_account_email
    resource_name_prefix = terraform.workspace
    region = var.region
}

module "api" {
    source = "../modules/api"
    network = google_compute_network.mev_api_network.name
    environment = var.environment
    ssh_tag = "webmev-backend-allow-ssh-${terraform.workspace}"
    cromwell_ip = module.cromwell.cromwell_ip
    api_machine_config = var.api_machine_config
    api_os_image = var.api_os_image
    domain = var.domain
    managed_dns_zone = var.managed_dns_zone
    db_user = var.db_user
    root_db_passwd = var.root_db_passwd
    db_passwd = var.db_passwd
    db_name = var.db_name
    db_port = var.db_port
    db_host = google_sql_database_instance.mev_db_instance.connection_name
    commit_id = var.commit_id == "" ? data.external.git.result["branch"] : var.commit_id
    cromwell_bucket = module.cromwell.cromwell_bucket
    django_secret = var.django_secret
    frontend_domain = var.frontend_domain
    other_cors_origins = var.other_cors_origins
    django_superuser_email = var.django_superuser_email
    django_superuser_passwd = var.django_superuser_passwd
    email_backend = var.email_backend
    from_email = var.from_email
    gmail_access_token = var.gmail_access_token
    gmail_refresh_token = var.gmail_refresh_token
    gmail_client_id = var.gmail_client_id
    gmail_client_secret = var.gmail_client_secret
    sentry_url = var.sentry_url
    container_registry = var.container_registry
    docker_repo_org = var.docker_repo_org
    service_account_email = var.service_account_email
    ssl_cert = var.ssl_cert
    storage_location = var.storage_location
    enable_remote_job_runners = var.enable_remote_job_runners
    remote_job_runners = var.remote_job_runners
    resource_name_prefix = terraform.workspace
    region = var.region
}


resource "google_compute_global_address" "private_ip_address" {

  name          = "webmev-backend-${terraform.workspace}-private-ip-address"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.mev_api_network.id
}

resource "google_service_networking_connection" "private_vpc_connection" {

  network                 = google_compute_network.mev_api_network.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address.name]
}

resource "random_id" "db_name_suffix" {
  byte_length = 4
}

resource "google_sql_database_instance" "mev_db_instance" {

  database_version = "POSTGRES_12"
  name   = "webmev-${terraform.workspace}-db-${random_id.db_name_suffix.hex}"
  region = var.region
  deletion_protection = false
  depends_on = [google_service_networking_connection.private_vpc_connection]

  settings {
    tier = "db-g1-small"
    availability_type = "ZONAL"
    disk_size = 30
    disk_type = "PD_SSD"
    disk_autoresize = true

    backup_configuration {
        enabled = true
    }

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.mev_api_network.id
    }
  }
}