class cromwell::service () {
  service { 'supervisor':
    ensure => running,
    enable => true,
  }
}
