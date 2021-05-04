resource "google_compute_instance" "mev_server" {
  name                    = "webmev-backend-${var.environment}"
  machine_type            = var.api_machine_config.machine_type
  tags                    = [var.ssh_tag]

  metadata_startup_script = templatefile("../modules/api/provision.sh", 
    {
        cromwell_ip = var.cromwell_ip
    }
)

  boot_disk {
    initialize_params {
      image = var.api_os_image
      size = var.api_machine_config.disk_size_gb
    }
  }

  network_interface {
    network = var.network
    access_config {
    }
  }
}

