resource "google_compute_instance" "mev_server" {
  name                    = "webmev-backend-${var.environment}"
  machine_type            = var.api_machine_config.machine_type
  tags                    = [
                              var.ssh_tag, 
                              "backend-${var.environment}-allow-health-check"
                            ]

  metadata_startup_script = templatefile("${path.module}/mev_provision.sh", 
    {
        environment = var.environment,
        cromwell_ip = var.cromwell_ip,
        domain = var.domain,
        db_user = var.db_user,
        root_db_passwd = var.root_db_passwd
        db_passwd = var.db_passwd,
        db_name = var.db_name,
        db_port = var.db_port,
        db_host = var.db_host,
        repo = var.repo,
        django_secret = var.django_secret
        cromwell_bucket = var.cromwell_bucket,
        frontend_domain = var.frontend_domain,
        django_superuser_email = var.django_superuser_email,
        django_superuser_passwd = var.django_superuser_passwd,
        mev_storage_bucket = var.mev_storage_bucket,
        email_backend = var.email_backend,
        from_email = var.from_email,
        gmail_access_token = var.gmail_access_token,
        gmail_refresh_token = var.gmail_refresh_token,
        gmail_client_id = var.gmail_client_id,
        gmail_client_secret = var.gmail_client_secret,
        sentry_url = var.sentry_url,
        dockerhub_username = var.dockerhub_username,
        dockerhub_passwd = var.dockerhub_passwd,
        branch = var.branch
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

  service_account {
      scopes = ["cloud-platform"]
  }
}

# allows the load balancer health check to reach the VM
resource "google_compute_firewall" "allow_hc_firewall" {
  name    = "webmev-backend-healthcheck-firewall"
  network = var.network

  allow {
    protocol = "tcp"
    ports    = ["80"]
  }

  direction = "INGRESS"
  source_ranges = ["130.211.0.0/22","35.191.0.0/16"]
  target_tags = ["backend-${var.environment}-allow-health-check"]
}

resource "google_compute_global_address" "lb-static-ip" {
  name = "webmev-${var.environment}-lb-static-address"
}


resource "google_dns_record_set" "set" {
  name         = "${var.domain}."
  type         = "A"
  ttl          = 600
  managed_zone = var.managed_dns_zone
  rrdatas      = [google_compute_global_address.lb-static-ip.address]
}


resource "google_compute_instance_group" "mev_api_ig" {
  name        = "mev-api-${var.environment}-ig"
  description = "Instance group for the backend ${var.environment} server"

  instances = [
    google_compute_instance.mev_server.id
  ]

  named_port {
    name = "http"
    port = "80"
  }

  #zone = var.zone
}


resource "google_compute_health_check" "http-health-check" {
  name = "backend-${var.environment}-health-check"

  timeout_sec        = 2
  check_interval_sec = 5

  http_health_check {
    port = "80"
    port_name = "http"
    request_path = "/api/"
  }
}

resource "google_compute_backend_service" "backend_service" {
  name          = "mev-backend-${var.environment}-service"
  health_checks = [google_compute_health_check.http-health-check.id]
  protocol = "HTTP"
  port_name = "http"
  load_balancing_scheme = "EXTERNAL"
  backend {
    group = google_compute_instance_group.mev_api_ig.self_link
    balancing_mode = "UTILIZATION"
    capacity_scaler = 1.0
    max_utilization = 0.8
  }
}

resource "google_compute_url_map" "urlmap" {
  name = "mev-backend-${var.environment}-urlmap"

  default_service = google_compute_backend_service.backend_service.id

  host_rule {
    hosts = [var.domain]
    path_matcher = "backend-pm"
  }

  path_matcher {
    name = "backend-pm"
    default_service = google_compute_backend_service.backend_service.id

    path_rule {
      paths = ["/api"]
      service = google_compute_backend_service.backend_service.id
    }

  }
}

resource "google_compute_target_https_proxy" "mev_backend_lb" {
  name             = "backend-${var.environment}-https-proxy"
  url_map          = google_compute_url_map.urlmap.id
  ssl_certificates = [google_compute_managed_ssl_certificate.backend_ssl_cert.id]
}


resource "google_compute_managed_ssl_certificate" "backend_ssl_cert" {
  name = "mev-api-${var.environment}-ssl-cert"

  managed {
    domains = ["${var.domain}."]
  }
}


resource "google_compute_global_forwarding_rule" "https_fwd" {
  name       = "mev-api-${var.environment}-forwarding-rule"
  target     = google_compute_target_https_proxy.mev_backend_lb.id
  port_range = 443
  ip_address = google_compute_global_address.lb-static-ip.address
}

  
resource "google_compute_url_map" "https_redirect" {
  name            = "${var.environment}-backend-https-redirect"

  default_url_redirect {
    https_redirect         = true
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
    strip_query            = false
  }
}

resource "google_compute_target_http_proxy" "https_redirect" {
  name   = "backend-${var.environment}-http-proxy"
  url_map          = google_compute_url_map.https_redirect.id
}

resource "google_compute_global_forwarding_rule" "https_redirect" {
  name   = "mev-api-${var.environment}-lb-http"

  target = google_compute_target_http_proxy.https_redirect.id
  port_range = "80"
  ip_address = google_compute_global_address.lb-static-ip.address
}

