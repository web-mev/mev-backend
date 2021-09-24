class mevapi (
  # parameter values are assigned by Hiera if not set when class is declared
  # https://puppet.com/docs/puppet/6/hiera_automatic.html#class_parameters
  String $django_settings_module,
  String $app_user,
  String $project_root,
  String $secret_key,
  String $superuser_password,
  String $frontend_domain,
  String $backend_domain,
  String $site_name,
  String $cloud_platform,
  String $enable_remote_job_runners,
  Enum['CROMWELL'] $remote_job_runners,
  Enum['local', 'remote'] $storage_location,
  String $storage_credentials,
  String $local_storage_dirname,
  String $storage_bucket_name,
  String $max_download_size_bytes,
  String $social_backends,
  String $sentry_url,
  String $dockerhub_org,
  String $dockerhub_username,
  String $dockerhub_password,
  String $database_name,
  String $database_user,
  String $database_password,
  String $database_host_socket,
  String $database_port,
  Enum['dev', 'production'] $environment,
  String $data_dir,
  String $cromwell_server_url,
  String $cromwell_bucket,

) {
  $app_group = $app_user

  $mev_dependencies = [
    'build-essential',
    'apt-transport-https',
    'ca-certificates',
    'gnupg2',
    'software-properties-common',
    'zlib1g-dev',
    'libssl-dev',
    'libncurses5-dev',
    'libreadline-dev',
    'libbz2-dev',
    'libffi-dev',
    'liblzma-dev',
    'libsqlite3-dev',
    'libpq-dev',
    'wget',
    'supervisor',
    'nano',
    'git',
    'curl',
    'pkg-config',
    'netcat',
    'procps',
    'postgresql-12',
    'nginx',
    'default-jre'
  ]
  package { $mev_dependencies: }

  class { 'python':
    version => '3.8',
  }

  python::requirements { "${project_root}/mev/requirements.txt":
    pip_provider           => 'pip3',
    forceupdate            => true,
    fix_requirements_owner => false,
  }

  include rabbitmq

  file { "${project_root}/.env":
    ensure => file,
    content => epp('mevapi/.env.epp'),
    owner => $app_user,
    group => $app_group,
  }

  class { 'docker':
    docker_users => [$app_user],
  }
}
