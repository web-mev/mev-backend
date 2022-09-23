class cromwell::install () {
  $dependencies = [
    'apt-transport-https',
    'build-essential',
    'ca-certificates',
    'default-jre',
    'gnupg2',
    'software-properties-common',
    'supervisor',
  ]
  package { $dependencies: }

  $version = 81
  file { "/opt/cromwell.jar":
    source => "https://github.com/broadinstitute/cromwell/releases/download/${version}/cromwell-${version}.jar"
  }

  class { 'postgresql::server': }
}
