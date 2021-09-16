class mevbackend () {
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

  $project_root = $facts['virtual'] ? {
    'gce'        => '/opt/software/mev-backend',
    'virtualbox' => '/vagrant',
  }
  python::requirements { "${project_root}/mev/requirements.txt":
    pip_provider           => 'pip3',
    forceupdate            => true,
    fix_requirements_owner => false,
  }

  include rabbitmq

  $app_user = $facts['virtual'] ? {
    'gce'        => 'ubuntu',
    'virtualbox' => 'vagrant',
  }

  $conf_mode = $facts['virtual'] ? {
    'gce'        => 'production',
    'virtualbox' => 'dev',
  }

  $django_settings_module = "mev.settings_${conf_mode}"

  # file_line { 'django_settings_module':
  #   path => "/home/${app_user}/.profile",
  #   line => "export DJANGO_SETTINGS_MODULE=${django_settings_module}",
  # }

}
