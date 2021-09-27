output "cromwell_ip" {
    value = google_compute_instance.cromwell.network_interface.0.network_ip
}

output "cromwell_bucket" {
    value = google_storage_bucket.cromwell_bucket.url
}