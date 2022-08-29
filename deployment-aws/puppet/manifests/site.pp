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
  file { "/opt/cromwell-${version}.jar":
    source => "https://github.com/broadinstitute/cromwell/releases/download/${version}/cromwell-${version}.jar"
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

  if $platform == 'aws' {
    vcsrepo { $project_root:
      ensure   => present,
      provider => git,
      source   => 'https://github.com/web-mev/mev-backend.git',
    }
  }

  class { 'postgresql::server': }

  file { '/opt/cromwell.conf':
    ensure  => file,
    content => epp(
      "${project_root}/deployment-aws/manifests/cromwell.conf.epp",
      {
        'region'                  => $facts['aws_region'],
        'api_storage_bucket'      => $facts['api_storage_bucket'],
        'cromwell_storage_bucket' => $facts['cromwell_storage_bucket'],
      }
    ),
    owner   => $cromwell_user,
    group   => $cromwell_user,
  }
}
