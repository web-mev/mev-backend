class mevapi::django () {
  $root = "${mevapi::project_root}/mev"
  $secret_key = fqdn_rand_string(50)
  $static_root = '/srv/static'

  class { 'python':
    version => '3.8',
  }

  python::requirements { 'mev':
    requirements           => "${root}/requirements.txt",
    pip_provider           => 'pip3',
    forceupdate            => true,
    fix_requirements_owner => false,
  }

  file { 'dotenv':
    ensure  => file,
    path    => "${mevapi::project_root}/.env",
    content => epp('mevapi/.env.epp'),
    owner   => $mevapi::app_user,
    group   => $mevapi::app_group,
  }

  file { $static_root:
    ensure => directory,
    owner  => $mevapi::app_user,
    group  => $mevapi::app_group,
  }

  $manage = "/usr/bin/python3 ${root}/manage.py"

  exec { 'migrate':
    command => "${manage} migrate",
    user    => $mevapi::app_user,
    group   => $mevapi::app_group,
    require => [
      Python::Requirements['mev'],
      File['dotenv'],
    ],
  }
  ->
  exec { 'superuser':
    command     => "${manage} superuser --noinput --email ${mevapi::admin_email_csv}",
    environment => ["DJANGO_SUPERUSER_PASSWORD=${mevapi::django_superuser_password}"],
    user        => $mevapi::app_user,
    group       => $mevapi::app_group,
  }
  ->
  exec { 'collectstatic':
    command => "${manage} collectstatic --noinput",
    user    => $mevapi::app_user,
    group   => $mevapi::app_group,
    require => File[$static_root],
  }
}
