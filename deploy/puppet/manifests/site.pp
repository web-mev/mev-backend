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

  vcsrepo { '/opt/mev-backend':
    ensure   => present,
    provider => git,
    source   => 'https://github.com/web-mev/mev-backend.git',
  }
}

node /api/ {
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
    version => 'system',
  }

  if $facts['virtual'] == 'gce' {
    python::requirements { '/opt/software/mev-backend/mev/requirements.txt': }
  }
  else {
    python::requirements { '/vagrant/mev/requirements.txt': }
  }
}
