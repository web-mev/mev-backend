node /api/ {
  class { 'mevapi':
    admin_email_csv             => $facts['admin_email_csv'],
    aws_region                  => $facts['aws_region'],
    backend_domain              => $facts['backend_domain'],
    cloudwatch_log_group        => $facts['cloudwatch_log_group'],
    container_registry          => $facts['container_registry'],
    cromwell_bucket_name        => $facts['cromwell_bucket_name'],
    cromwell_server_ip          => $facts['cromwell_server_ip'],
    database_host               => $facts['database_host'],
    database_superuser          => $facts['database_superuser'],
    database_superuser_password => $facts['database_superuser_password'],
    database_user_password      => $facts['database_user_password'],
    data_volume_device_name     => $facts['data_volume_device_name'],
    django_cors_origins         => $facts['django_cors_origins'],
    django_settings_module      => $facts['django_settings_module'],
    django_superuser_email      => $facts['django_superuser_email'],
    django_superuser_password   => $facts['django_superuser_password'],
    email_host_user             => $facts['email_host_user'],
    email_host_password         => $facts['email_host_password'],
    enable_remote_job_runners   => $facts['enable_remote_job_runners'],
    from_email                  => $facts['from_email'],
    frontend_domain             => $facts['frontend_domain'],
    globus_app_client_id        => $facts['globus_app_client_id'],
    globus_app_client_secret    => $facts['globus_app_client_secret'],
    globus_endpoint_id          => $facts['globus_endpoint_id'],
    storage_location            => $facts['storage_location'],
    storage_bucket_name         => $facts['storage_bucket_name'],
  }
}

node /cromwell/ {
  class { 'cromwell':
    api_storage_bucket   => $facts['api_storage_bucket'],
    aws_region           => $facts['aws_region'],
    cloudwatch_log_group => $facts['cloudwatch_log_group'],
    job_queue            => $facts['cromwell_job_queue'],
    storage_bucket       => $facts['cromwell_storage_bucket'],
  }
}
