# Allow http into that machine
resource "google_compute_firewall" "cromwell_http" {
  name    = "cromwell-${var.environment}-http"
  network = var.network

  allow {
    protocol                 = "tcp"
    ports                    = ["8000"]
  }

  target_tags = ["cromwell-8000"]
}


resource "google_compute_instance" "cromwell" {
  name                    = "cromwell-${var.environment}"
  machine_type            = var.cromwell_machine_config.machine_type
  tags                    = ["cromwell-8000", var.ssh_tag]
  labels                  = {
                                "app" = "mev-api"
                                "environment" = var.environment
                            }

  metadata_startup_script = templatefile("${path.module}/cromwell_provision.sh", 
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
    network = var.network
  }

  service_account {
      email = var.service_account_email
      scopes = ["cloud-platform"]
  }
}
