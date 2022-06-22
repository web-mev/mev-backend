# @summary Install and configure WebMeV API
class mevapi (
  # parameter values are assigned by Hiera if not set when class is declared
  # https://puppet.com/docs/puppet/6/hiera_automatic.html#class_parameters
  String                    $django_settings_module,
  String                    $app_user,
  String                    $project_root,
  String                    $secret_key,
  String                    $django_allowed_hosts,
  String                    $django_cors_origins,
  String                    $frontend_domain,
  String                    $backend_domain,
  String                    $site_name,
  String                    $cloud_platform,
  String                    $enable_remote_job_runners,
  Enum['CROMWELL']          $remote_job_runners,
  Enum['local', 'remote']   $storage_location,
  String                    $storage_credentials,
  String                    $local_storage_dirname,
  String                    $storage_bucket_name,
  String                    $max_download_size_bytes,
  String                    $social_backends,
  String                    $sentry_url,
  String                    $docker_repo_org,
  String                    $container_registry,
  String                    $database_name,
  String                    $database_user,
  String                    $database_password,
  String                    $database_host_socket,
  String                    $database_port,
  Enum['dev', 'production'] $environment,
  String                    $cromwell_server_url,
  String                    $cromwell_bucket,
  String                    $email_backend_choice,
  String                    $from_email,
  String                    $email_host,
  String                    $email_port,
  String                    $email_host_user,
  String                    $email_host_password,
  String                    $admin_email_csv
) {
  $app_group = $app_user
  $django_root = "${project_root}/mev"
  $log_dir = '/var/log/mev'
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
  $solr_home = "${data_root}/solr"

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
    'supervisor',
    'nano',
    'git',
    'curl',
    'pkg-config',
    'netcat',
    'procps',
    'postgresql-12',
    'default-jre'
  ]
  package { $mev_dependencies: }

  class { 'python':
    version => '3.8',
  }

  python::requirements { "${django_root}/requirements.txt":
    pip_provider           => 'pip3',
    forceupdate            => true,
    fix_requirements_owner => false,
  }

  include rabbitmq

  file { concat([$data_root], $data_dirs):
    ensure => directory,
    owner  => $app_user,
    group  => $app_group,
  }

  class { 'solr':
    version     => '8.11.1',  # make sure luceneMatchVersion in all solrconfig.xml files matches this version
    solr_home   => $solr_home,
    schema_name => 'schema.xml',  # classic schema
  }
  file { "${solr_home}/solr.xml":
    ensure => file,
    source => "${project_root}/solr/solr.xml",
    owner  => $::solr::solr_user,
    group  => $::solr::solr_user,
  }
  solr::core { 'tcga-rnaseq':
    schema_src_file     => "${project_root}/solr/tcga-rnaseq/schema.xml",
    solrconfig_src_file => "${project_root}/solr/tcga-rnaseq/solrconfig.xml",
  }
  solr::core { 'target-rnaseq':
    schema_src_file     => "${project_root}/solr/target-rnaseq/schema.xml",
    solrconfig_src_file => "${project_root}/solr/target-rnaseq/solrconfig.xml",
  }
  solr::core { 'gtex-rnaseq':
    schema_src_file     => "${project_root}/solr/gtex-rnaseq/schema.xml",
    solrconfig_src_file => "${project_root}/solr/gtex-rnaseq/solrconfig.xml",
  }

  file { "${project_root}/.env":
    ensure  => file,
    content => epp('mevapi/.env.epp'),
    owner   => $app_user,
    group   => $app_group,
  }

  class { 'docker':
    docker_users => [$app_user],
  }

  # Supervisor configuration
  file {
    default:
      ensure => file,;
    '/etc/supervisor/supervisord.conf':
      content => epp('mevapi/supervisor/supervisord.conf.epp'),;
    '/etc/supervisor/conf.d/gunicorn.conf':
      content => epp('mevapi/supervisor/gunicorn.conf.epp'),;
    '/etc/supervisor/conf.d/celery_beat.conf':
      content => epp('mevapi/supervisor/celery_beat.conf.epp'),;
    '/etc/supervisor/conf.d/celery_worker.conf':
      content => epp('mevapi/supervisor/celery_worker.conf.epp'),;
  }
  if $facts['virtual'] == 'gce' {
    file { '/etc/supervisor/conf.d/cloud_sql_proxy.conf':
      ensure  => file,
      content => epp('mevapi/supervisor/cloud_sql_proxy.conf.epp'),
    }
  }

  # Nginx configuration
  class { 'nginx':
    confd_purge => true,  # remove default config
  }
  nginx::resource::upstream { 'mev_app':
    members => {
      'gunicorn' => {
        server       => 'unix:/tmp/gunicorn.sock',
        # always retry an upstream even if it failed to return a good HTTP response
        fail_timeout => '0s',
      }
    }
  }
  # This map helps in situations where the request doesn't reach the
  # gunicorn application server. An example is when the payload
  # exceeds the client_max_body_size. In that case, nginx immediately
  # responds with a 413, and the frontend is unable to
  # see the response since it was lacking the 'Access-Control-Allow-Origin'
  # header. This map skips editing in the case where this header exists and
  # adds it in the case where it does not.
  nginx::resource::map { 'cors_origin':
    string   => '$upstream_http_access_control_allow_origin',
    default  => "''",
    mappings => {
      "''" => '$http_origin'
    },
  }
  nginx::resource::server { $backend_domain:
    listen_port          => 80,
    client_max_body_size => '256m',
    use_default_location => false,
    index_files          => [],
    locations            => {
      'root'   => {
        location         => '/',
        add_header       => {
          'Access-Control-Allow-Origin' => { '$cors_origin' => 'always' },
        },
        proxy            => 'http://mev_app',
        proxy_redirect   => 'off',
        proxy_set_header => [
          'Host              $host',
          'X-Forwarded-For   $proxy_add_x_forwarded_for',
          'X-Forwarded-Proto $scheme',
          'X-Forwarded-Host  $host',
          'X-Forwarded-Port  $server_port',
        ],
      },
      'static' => {
        location       => '/static/',
        location_alias => '/www/static/',
        index_files    => [],
      },
    },
  }
  nginx::resource::server { 'default':
    server_name         => ['_'],
    listen_port         => 80,
    listen_options      => "default_server",
    index_files         => [],
    access_log          => 'absent',
    error_log           => 'absent',
    location_custom_cfg => {
      'return' => 444,
    }
  }

  file { $log_dir:
    ensure => directory,
    owner  => $app_user,
    group  => $app_group,
  }
}
