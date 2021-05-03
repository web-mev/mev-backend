terraform {
  required_version = "~> 0.14.0"
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


# this shows up in the console. OK
resource "google_compute_network" "mev_api_network" {
    name           = "mev-${var.environment}-network"
}

# Show up correctly in console. OK
#  This firewall allows ssh connections to the VMs
resource "google_compute_firewall" "default_ssh" {
  name    = "mev-${var.environment}-allow-ssh"
  network = google_compute_network.mev_api_network.name

  allow {
    protocol                 = "tcp"
    ports                    = ["22"]
  }

  target_tags = ["allow-ssh"]
}

# Show up correctly in console. OK
#  This firewall allows http/s connections to the mev api VM
resource "google_compute_firewall" "mev_firewall" {
  name    = "mev-${var.environment}-firewall"
  network = google_compute_network.mev_api_network.name

  allow {
    protocol                 = "tcp"
    ports                    = ["80", "443"]
  }

  target_tags = ["web"]
}


# Show up correctly in console. OK
# This firewall allows inbound traffic on port 8000 ONLY
# from the VM hosting the MEV application
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


# Shows up correctly in console. OK
# This firewall allows the healthcheck on the VMs
# The source range IPs taken from google's documentation
resource "google_compute_firewall" "healthcheck_firewall" {
  name    = "healthcheck-${var.environment}-firewall"
  network = google_compute_network.mev_api_network.name

  allow {
    protocol                 = "tcp"
    ports                    = ["80", "443"]
  }

  source_ranges = ["130.211.0.0/22","35.191.0.0/16"]
  target_tags = ["allow-healthcheck"]
}



# Shows up correctly in console. Links to the main API VM. OK
resource "google_compute_address" "mev-static-ip" {
  name = "mev-${var.environment}-static-address"
}

# Shows up correctly in console. Links to the cromwell machine. OK
resource "google_compute_address" "cromwell-static-ip" {
  name = "cromwell-${var.environment}-static-address"
}

# Shows up in console. Mentions being in use by "https-content-rule".
# Returns a google "broken robot" 404 if typed into browser.
# Probably due to failure of urlMap below
resource "google_compute_address" "lb-ipv4-ip" {
  name = "lb-ipv4-${var.environment}-static-address"
}

# Google docs make mention of supporting IPV6, but can't get this to work
#resource "google_compute_address" "lb-ipv6-ip" {
#  name = "lb-ipv6-${var.environment}-static-address"
#  ip_version = "IPV6"
#}


# The main API VM. Doesn't actually run the MEV api.
# For now, simply installs apache and serves a file that echoes the hostname
resource "google_compute_instance" "mev_api" {
  name                    = "test-mev-api-${var.environment}"
  machine_type            = var.api_machine_config.machine_type
  tags                    = ["web", "mev-api", "allow-ssh", "allow-healthcheck"]
  labels                  = {
                                "app" = "mev-api"
                                "environment" = var.environment
                            }

  metadata_startup_script = file("demo_provision.sh")

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

# The "cromwell" VM. 
# Doesn't actually run the Cromwell server.
# For now, simply installs apache and serves a file that echoes the hostname
resource "google_compute_instance" "cromwell" {
  name                    = "cromwell-${var.environment}"
  machine_type            = var.cromwell_machine_config.machine_type
  tags                    = ["cromwell-8000", "allow-ssh", "allow-healthcheck"]
  labels                  = {
                                "app" = "mev-api"
                                "environment" = var.environment
                            }

  metadata_startup_script = file("demo_provision.sh")

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

# Shows up in console and includes the single "API" server.OK
resource "google_compute_instance_group" "mev_api_ig" {
  name        = "mev-api-ig"
  description = "Terraform test instance group"

  instances = [
    google_compute_instance.mev_api.id
  ]

  named_port {
    name = "http"
    port = "80"
  }

  zone = var.zone
}

# Shows up in console and shows the "cromwell" server as its only member. OK
resource "google_compute_instance_group" "mev_cromwell_ig" {
  name        = "mev-cromwell-ig"
  description = "Terraform test instance group"

  instances = [
    google_compute_instance.cromwell.id
  ]

  named_port {
    name = "http"
    port = "80"
  }

  zone = var.zone
}


# Shows up in console and is "in use by" the api and cromwell backend services. OK
resource "google_compute_health_check" "http-health-check" {
  name = "http-health-check"

  timeout_sec        = 2
  check_interval_sec = 5

  http_health_check {
    port = "80"
    port_name = "http"
  }
}

resource "google_compute_backend_service" "api_backend_service" {
  name          = "api-backend-service"
  health_checks = [google_compute_health_check.http-health-check.id]
  backend {
    group = google_compute_instance_group.mev_api_ig.self_link
  }
}

resource "google_compute_backend_service" "cromwell_backend_service" {
  name          = "cromwell-backend-service"
  health_checks = [google_compute_health_check.http-health-check.id]
  backend {
    group = google_compute_instance_group.mev_cromwell_ig.self_link
  }
}

resource "google_compute_url_map" "urlmap" {
  name = "myurlmap"
  description = "some desc"

  default_service = google_compute_backend_service.api_backend_service.id


  path_matcher {
    name = "xyz"
    default_service = google_compute_backend_service.api_backend_service.id

    path_rule {
      paths = ["/api"]
      service = google_compute_backend_service.api_backend_service.id
    }

    path_rule {
      paths = ["/cromwell"]
      service = google_compute_backend_service.cromwell_backend_service.id
    }

  }
}


# Don't see this in the console. Likely due to the url map failing- then can't create this.
resource "google_compute_target_https_proxy" "my-test-lb" {
  name             = "test-proxy"
  url_map          = google_compute_url_map.urlmap.id
  ssl_certificates = [google_compute_managed_ssl_certificate.default.id]
}

# Failed to create this-- can't find via console, but using gcloud:
#     $ gcloud compute ssl-certificates list
#     NAME           TYPE     CREATION_TIMESTAMP             EXPIRE_TIME  MANAGED_STATUS
#     mev-test-cert  MANAGED  2021-05-03T06:47:37.634-07:00               PROVISIONING
#          ssltest.tm4.org: FAILED_NOT_VISIBLE
resource "google_compute_managed_ssl_certificate" "default" {
  name = "mev-test-cert"

  managed {
    domains = ["ssltest.tm4.org."]
  }
}

# No LB created, so this isn't there:
#     $ gcloud compute forwarding-rules list
#       NAME                              REGION    IP_ADDRESS     IP_PROTOCOL  TARGET
# https-content-rule                          xx.xxx.xxx.xx  TCP          https-lb-proxy
# a329e6aba032011e79d5c42010af0019  us-east1  xx.xxx.xx.x    TCP          ...
resource "google_compute_global_forwarding_rule" "test-fwd" {
  name       = "mev-forwarding-rule"
  target     = google_compute_target_https_proxy.my-test-lb.id
  port_range = 443
}


# Depends on other failed resources, so obviously not created.
resource "google_dns_record_set" "set" {
  name         = "ssltest.tm4.org."
  type         = "A"
  ttl          = 600
  managed_zone = var.managed_dns_zone
  #managed_zone = google_dns_managed_zone.zone.id
  rrdatas      = [google_compute_global_forwarding_rule.test-fwd.ip_address]
}
