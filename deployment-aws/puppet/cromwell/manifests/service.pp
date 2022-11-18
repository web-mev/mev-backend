class cromwell::service () {
  service { 'supervisor':
    ensure => running,
    enable => true,
  }

  service { 'amazon-cloudwatch-agent':
    ensure => running,
    enable => true,
  }
}
