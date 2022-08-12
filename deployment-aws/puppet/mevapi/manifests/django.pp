class mevapi::django () {
  $root = "${mevapi::project_root}/mev"
  $manage = "/usr/bin/python3 ${root}/manage.py"

  $static_root = '/www/static'
  file { $static_root:
    ensure => directory,
    owner  => $mevapi::app_user,
    group  => $mevapi::app_group,
  }

  file { "${mevapi::project_root}/.env":
    ensure  => file,
    content => epp('mevapi/.env.epp'),
    owner   => $mevapi::app_user,
    group   => $mevapi::app_group,
  }
  ->
  exec { 'migrate':
    command => "${manage} migrate",
    user    => $mevapi::app_user,
    group   => $mevapi::app_group,
  }
  ->
  exec { 'superuser':
    command     => "${manage} superuser --noinput --username admin --email ${mevapi::admin_email_csv}",
    environment => ["DJANGO_SUPERUSER_PASSWORD=${mevapi::django_superuser_password}"],
    user        => $mevapi::app_user,
    group       => $mevapi::app_group,
  }

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
}
