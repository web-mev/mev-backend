resource "google_compute_instance" "mev_server" {
  name         = "${var.resource_name_prefix}-webmev-api"
  machine_type = var.api_machine_config.machine_type
  tags         = [
    var.ssh_tag,
    "${var.resource_name_prefix}-webmev-api-allow-health-check"
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
        commit_id = var.commit_id,
        django_secret = var.django_secret
        cromwell_bucket = var.cromwell_bucket,
        frontend_domain = var.frontend_domain,
        load_balancer_ip = google_compute_global_address.lb-static-ip.address,
        other_cors_origins = var.other_cors_origins,
        django_superuser_email = var.django_superuser_email,
        django_superuser_passwd = var.django_superuser_passwd,
        mev_storage_bucket = google_storage_bucket.api_bucket.url
        storage_location = var.storage_location,
        email_backend = var.email_backend,
        from_email = var.from_email,
        gmail_access_token = var.gmail_access_token,
        gmail_refresh_token = var.gmail_refresh_token,
        gmail_client_id = var.gmail_client_id,
        gmail_client_secret = var.gmail_client_secret,
        admin_email_csv = var.admin_email_csv,
        sentry_url = var.sentry_url,
        container_registry = var.container_registry,
        docker_repo_org = var.docker_repo_org,
        enable_remote_job_runners = var.enable_remote_job_runners,
        remote_job_runners = var.remote_job_runners,
        service_account_email = var.service_account_email
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
      email = var.service_account_email
      scopes = ["cloud-platform"]
  }
}

resource "google_storage_bucket" "api_bucket" {
  name = "webmev-storage-${var.resource_name_prefix}"
  location = upper(var.region)

  cors {
    origin = ["*"]
    method = ["GET", "OPTIONS"]
    response_header = ["*"]
    max_age_seconds = 3600
  }
}

# allows the load balancer health check to reach the VM
resource "google_compute_firewall" "allow_hc_firewall" {
  name    = "${var.resource_name_prefix}-webmev-api-healthcheck-firewall"
  network = var.network

  allow {
    protocol = "tcp"
    ports    = ["80"]
  }

  direction = "INGRESS"
  source_ranges = ["130.211.0.0/22","35.191.0.0/16"]
  target_tags = ["${var.resource_name_prefix}-webmev-api-allow-health-check"]
}

resource "google_compute_global_address" "lb-static-ip" {
  name = "${var.resource_name_prefix}-webmev-api-lb-static-address"
}

resource "google_dns_record_set" "set" {
  name         = "${var.domain}."
  type         = "A"
  ttl          = 600
  managed_zone = var.managed_dns_zone
  rrdatas      = [google_compute_global_address.lb-static-ip.address]
}

resource "google_compute_instance_group" "mev_api_ig" {
  name        = "${var.resource_name_prefix}-webmev-api-ig"
  description = "Instance group for the backend ${var.environment} server"

  instances = [
    # self_link to avoid invalid instance URL error: https://stackoverflow.com/a/65899240
    google_compute_instance.mev_server.self_link
  ]

  named_port {
    name = "http"
    port = "80"
  }
}

resource "google_compute_health_check" "http-health-check" {
  name               = "${var.resource_name_prefix}-webmev-api-health-check"
  timeout_sec        = 2
  check_interval_sec = 5

  http_health_check {
    port         = "80"
    port_name    = "http"
    request_path = "/api/"
    host         = var.domain
  }
}

resource "google_compute_backend_service" "backend_service" {
  name                  = "${var.resource_name_prefix}-webmev-api-service"
  health_checks         = [google_compute_health_check.http-health-check.id]
  protocol              = "HTTP"
  port_name             = "http"
  load_balancing_scheme = "EXTERNAL"

  backend {
    group           = google_compute_instance_group.mev_api_ig.self_link
    balancing_mode  = "UTILIZATION"
    capacity_scaler = 1.0
    max_utilization = 0.8
  }
}

resource "google_compute_url_map" "urlmap" {
  name            = "${var.resource_name_prefix}-webmev-api-urlmap"
  default_service = google_compute_backend_service.backend_service.id

  host_rule {
    hosts        = [var.domain]
    path_matcher = "backend-pm"
  }

  path_matcher {
    name            = "backend-pm"
    default_service = google_compute_backend_service.backend_service.id

    path_rule {
      paths   = ["/api"]
      service = google_compute_backend_service.backend_service.id
    }
  }
}

resource "google_compute_target_https_proxy" "mev_backend_lb" {
  name             = "${var.resource_name_prefix}-webmev-api-https-proxy"
  url_map          = google_compute_url_map.urlmap.id
  ssl_certificates = [var.ssl_cert]
}

resource "google_compute_global_forwarding_rule" "https_fwd" {
  name       = "${var.resource_name_prefix}-webmev-api-forwarding-rule"
  target     = google_compute_target_https_proxy.mev_backend_lb.id
  port_range = 443
  ip_address = google_compute_global_address.lb-static-ip.address
}

resource "google_compute_url_map" "https_redirect" {
  name = "${var.resource_name_prefix}-webmev-api-https-redirect"

  default_url_redirect {
    https_redirect         = true
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
    strip_query            = false
  }
}

resource "google_compute_target_http_proxy" "https_redirect" {
  name    = "${var.resource_name_prefix}-webmev-api-http-proxy"
  url_map = google_compute_url_map.https_redirect.id
}

resource "google_compute_global_forwarding_rule" "https_redirect" {
  name       = "${var.resource_name_prefix}-webmev-api-lb-http"
  target     = google_compute_target_http_proxy.https_redirect.id
  port_range = "80"
  ip_address = google_compute_global_address.lb-static-ip.address
}
