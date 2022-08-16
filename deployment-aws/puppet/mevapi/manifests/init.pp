# @summary Install and configure WebMEV API server
#
# Provisions WebMEV API server on Vagrant and AWS
#
# @example
#   class { 'mevapi':
#   }
class mevapi (
  String                  $admin_email_csv,
  Optional[String]        $app_user,
  String                  $backend_domain,
  Optional[String]        $container_registry,
  String                  $database_host,
  Optional[String]        $database_superuser,
  Optional[String]        $database_superuser_password,
  String                  $database_user_password,
  Optional[String]        $django_settings_module,
  String                  $django_superuser_password,
  Optional[String]        $email_backend_choice,
  String                  $email_host,
  String                  $email_host_user,
  String                  $email_host_password,
  String                  $email_port,
  Optional[String]        $enable_remote_job_runner,
  Optional[String]        $from_email,
  String                  $frontend_domain,
  Optional[String]        $project_root,
  String                  $sentry_url,
  Optional[String]        $site_name,
  Enum['local', 'remote'] $storage_location,
) {
  if $facts['virtual'] == 'kvm' {
    $platform = 'aws'
  } else {
    # gce or virtualbox
    $platform = $facts['virtual']
  }

  $app_group = $app_user
  $database_user = $app_user
  $local_storage_dirname = "user_resources"

  $log_dir = '/var/log/mev'
  file { $log_dir:
    ensure => directory,
    owner  => $app_user,
    group  => $app_group,
  }

  $data_root = '/data'
  $data_dirs = [
    "${data_root}/pending_user_uploads",
    "${data_root}/resource_validation_tmp",
    "${data_root}/resource_cache",
    "${data_root}/operation_staging",
    "${data_root}/operations",
    "${data_root}/operation_executions",
    "${data_root}/public_data",
  ]
  file { concat([$data_root], $data_dirs):
    ensure => directory,
    owner  => $app_user,
    group  => $app_group,
  }

  if $platform == 'virtualbox' {
    # JSON file containing the credentials to authenticate with the Google storage API
    # no actual need this for local dev but it needs to be populated for the app to startup properly
    file { "${project_root}/storage_credentials.json":
      ensure => file,
      owner  => $app_user,
      group  => $app_group,
    }
  }

  $mev_dependencies = [
    'build-essential',
    'apt-transport-https',
    'ca-certificates',
    'gnupg2',
    'zlib1g-dev',
    'libssl-dev',
    'libncurses5-dev',
    'libreadline-dev',
    'libbz2-dev',
    'libffi-dev',
    'liblzma-dev',
    'libsqlite3-dev',
    'libpq-dev',
    'nano',
    'git',
    'curl',
    'pkg-config',
    'netcat',
    'procps',
    'default-jre'
  ]
  package { $mev_dependencies: }

  class { 'rabbitmq':
    manage_python => false,
  }

  class { 'docker':
    docker_users => [$app_user],
  }

  contain mevapi::django
  contain mevapi::nginx
  contain mevapi::postgresql
  contain mevapi::solr
  contain mevapi::supervisor

  Class['mevapi::postgresql']
  ->
  Class['mevapi::django']
  ~>
  Class['mevapi::supervisor']
  ->
  Class['mevapi::nginx']
}
