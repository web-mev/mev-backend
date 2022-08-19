node /api/ {
  class { 'mevapi':
    django_settings_module    => $facts['django_settings_module'],
    app_user                  => $facts['app_user'],
    project_root              => $facts['project_root'],
    secret_key                => $facts['secret_key'],
    django_allowed_hosts      => $facts['django_allowed_hosts'],
    django_cors_origins       => $facts['django_cors_origins'],
    frontend_domain           => $facts['frontend_domain'],
    backend_domain            => $facts['backend_domain'],
    site_name                 => $facts['site_name'],
    django_static_root        => $facts['django_static_root'],
    cloud_platform            => $facts['cloud_platform'],
    enable_remote_job_runners => $facts['enable_remote_job_runners'],
    remote_job_runners        => $facts['remote_job_runners'],
    storage_location          => $facts['storage_location'],
    storage_credentials       => $facts['storage_credentials'],
    local_storage_dirname     => $facts['local_storage_dirname'],
    storage_bucket_name       => $facts['storage_bucket_name'],
    max_download_size_bytes   => $facts['max_download_size_bytes'],
    social_backends           => $facts['social_backends'],
    sentry_url                => $facts['sentry_url'],
    docker_repo_org           => $facts['docker_repo_org'],
    container_registry        => $facts['container_registry'],
    database_name             => $facts['database_name'],
    database_user             => $facts['database_user'],
    database_password         => $facts['database_password'],
    database_host_socket      => $facts['database_host_socket'],
    database_port             => $facts['database_port'],
    environment               => $facts['environment'],
    cromwell_server_url       => $facts['cromwell_server_url'],
    cromwell_bucket           => $facts['cromwell_bucket'],
    email_backend_choice      => $facts['email_backend_choice'],
    from_email                => $facts['from_email'],
    email_host                => $facts['email_host'],
    email_port                => $facts['email_port'],
    email_host_user           => $facts['email_host_user'],
    email_host_password       => $facts['email_host_password'],
    admin_email_csv           => $facts['admin_email_csv']
  }
}

node /cromwell/ {
  package { 'default-jre': }

  file { '/opt/cromwell-81.jar':
    source => 'https://github.com/broadinstitute/cromwell/releases/download/81/cromwell-81.jar'
  }

  $cromwell_user = 'cromwell-runner'

  user { $cromwell_user:
    ensure => present,
  }

  file { '/var/log/cromwell':
    ensure => directory,
    owner  => $cromwell_user,
    group  => $cromwell_user,
  }

  vcsrepo { '/opt/mev-backend':
    ensure   => present,
    provider => git,
    source   => 'https://github.com/web-mev/mev-backend.git',
  }
}
