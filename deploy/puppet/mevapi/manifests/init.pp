class mevapi (
  # parameter values are assigned by Hiera if not set when class is declared
  # https://puppet.com/docs/puppet/6/hiera_automatic.html#class_parameters
  String $app_user,
  String $project_root,
  String $conf_mode,
) {
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
    'docker.io',
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

  $django_settings_module = "mev.settings_${conf_mode}"

  # file_line { 'django_settings_module':
  #   path => "/home/${app_user}/.profile",
  #   line => "export DJANGO_SETTINGS_MODULE=${django_settings_module}",
  # }
}
