class cromwell::service () {
  service { 'supervisor':
    ensure => running,
    enable => true,
  }

  # exec { 'cloudwatch_agent':
  #   command => "${cromwell::cloudwatch_agent_dir}/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -s -c file:/etc/cloudwatch_agent_config.json",
  #   owner   => $cromwell::user,
  #   group   => $cromwell::user
  # }
}
