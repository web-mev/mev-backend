class cromwell::service () {
  service { 'supervisor':
    ensure => running,
    enable => true,
  }

  if $cromwell::platform == 'aws' {
    service { 'amazon-cloudwatch-agent':
      ensure => running,
      enable => true,
    }
  }
}
