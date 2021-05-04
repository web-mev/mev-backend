node /cromwell/ {
  package { 'default-jre': }

  file { '/opt/cromwell-60.jar':
    source => 'https://github.com/broadinstitute/cromwell/releases/download/60/cromwell-60.jar'
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
}

node /api/ {

}
