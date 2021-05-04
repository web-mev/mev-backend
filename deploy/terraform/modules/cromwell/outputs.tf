output "cromwell_ip" {
    value = google_compute_instance.cromwell.network_interface.0.network_ip
}