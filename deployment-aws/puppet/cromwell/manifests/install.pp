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

  file { "/opt/amazon-cloudwatch-agent.deb":
    source => "https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb"
  }

  package { "cloudwatch_agent":
    provider  => "dpkg",
    ensure    => installed,
    source    => "/opt/amazon-cloudwatch-agent.deb"
  }

  class { 'postgresql::server': }
}
