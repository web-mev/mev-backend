node /api/ {
  class { 'mevapi':
    admin_email_csv             => $facts['admin_email_csv'],
    backend_domain              => $facts['backend_domain'],
    container_registry          => $facts['container_registry'],
    database_host               => $facts['database_host'],
    database_superuser          => $facts['database_superuser'],
    database_superuser_password => $facts['database_superuser_password'],
    database_user_password      => $facts['database_user_password'],
    django_settings_module      => $facts['django_settings_module'],
    django_superuser_password   => $facts['django_superuser_password'],
    email_host_user             => $facts['email_host_user'],
    email_host_password         => $facts['email_host_password'],
    enable_remote_job_runners   => $facts['enable_remote_job_runners'],
    from_email                  => $facts['from_email'],
    frontend_domain             => $facts['frontend_domain'],
    storage_location            => $facts['storage_location'],
    storage_bucket_name         => $facts['storage_bucket_name'],
    cromwell_bucket_name        => $facts['cromwell_bucket_name'],
    cromwell_server_url         => $facts['cromwell_server_url'],
  }
}

node /cromwell/ {
  if $facts['virtual'] == 'kvm' {
    $platform = 'aws'
  } else {
    # gce or virtualbox
    $platform = $facts['virtual']
  }

  $project_root = $platform ? {
    'aws'        => '/srv/mev-backend',
    'virtualbox' => '/vagrant',
  }

  $dependencies = [
    'apt-transport-https',
    'build-essential',
    'ca-certificates',
    'default-jre',
    'gnupg2',
    'software-properties-common',
    'supervisor',
  ]
  package { $dependencies: }

  $version = 81
  file { "/opt/cromwell.jar":
    source => "https://github.com/broadinstitute/cromwell/releases/download/${version}/cromwell-${version}.jar"
  }

  $cromwell_user = 'ubuntu'
  $cromwell_log_dir = '/var/log/cromwell'
  $cromwell_db_password = fqdn_rand_string(6)

  file { [$cromwell_log_dir, '/cromwell-workflow-logs']:
    ensure => directory,
    owner  => $cromwell_user,
    group  => $cromwell_user,
  }

  file { '/etc/cromwell.conf':
    ensure  => file,
    content => epp(
      "${project_root}/deployment-aws/puppet/manifests/cromwell.conf.epp",
      {
        'region'                  => $facts['aws_region'],
        'api_storage_bucket'      => $facts['api_storage_bucket'],
        'cromwell_storage_bucket' => $facts['cromwell_storage_bucket'],
        'cromwell_job_queue'      => $facts['cromwell_job_queue'],
        'cromwell_db_user'        => $cromwell_user,
        'cromwell_db_password'    => $cromwell_db_password,
      }
    ),
    owner   => $cromwell_user,
    group   => $cromwell_user,
  }

  file { '/etc/supervisor/conf.d/cromwell.conf':
    ensure  => file,
    content => epp(
      "${project_root}/deployment-aws/puppet/manifests/cromwell-supervisor.conf.epp",
      {
        'cromwell_user'    => $cromwell_user,
        'cromwell_log_dir' => $cromwell_log_dir,
      }
    ),
    owner   => $cromwell_user,
    group   => $cromwell_user,
  }

  class { 'postgresql::server': }

  postgresql::server::db { 'cromwell':
    user     => $cromwell_user,
    password => $cromwell_db_password,
  }
  ~>
  service { 'supervisor':
    ensure => running,
    enable => true,
  }
}
