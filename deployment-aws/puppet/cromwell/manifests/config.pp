class cromwell::config () {
  file { [$cromwell::log_dir, '/cromwell-workflow-logs']:
    ensure => directory,
    owner  => $cromwell::user,
    group  => $cromwell::user,
  }

  file { '/etc/cromwell.conf':
    ensure  => file,
    content => epp('cromwell/cromwell.conf.epp'),
    owner   => $cromwell::user,
    group   => $cromwell::user,
  }

  file { '/etc/supervisor/conf.d/cromwell.conf':
    ensure  => file,
    content => epp('cromwell/cromwell-supervisor.conf.epp'),
    owner   => $cromwell::user,
    group   => $cromwell::user,
  }

  postgresql::server::db { 'cromwell':
    user     => $cromwell::user,
    password => $cromwell::db_password,
  }
}