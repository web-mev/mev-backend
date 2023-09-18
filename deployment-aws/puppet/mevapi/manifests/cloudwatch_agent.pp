class mevapi::cloudwatch_agent () {
  if $mevapi::platform == 'aws' {
    $cloudwatch_agent_dir = '/opt/aws/amazon-cloudwatch-agent'
    $cloudwatch_agent_deb = '/tmp/amazon-cloudwatch-agent.deb'

    file { $cloudwatch_agent_deb:
      ensure => present,
      source => 'https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb',
    }

    package { 'amazon-cloudwatch-agent':
      provider => dpkg,
      source   => $cloudwatch_agent_deb
    }
    ->
    # Note that the config file we created here controls which log files
    # and machine metrics are monitored. Metrics are kept for 15 days on a rolling basis
    # https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_concepts.html#Metric
    file { "${cloudwatch_agent_dir}/etc/amazon-cloudwatch-agent.json":
      ensure  => file,
      content => epp('mevapi/cloudwatch_config.json.epp'),
    }
    ~>
    exec { 'cloudwatch_agent':
      command => "${cloudwatch_agent_dir}/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 \
        -c file:${cloudwatch_agent_dir}/etc/amazon-cloudwatch-agent.json",
      creates => "${cloudwatch_agent_dir}/etc/amazon-cloudwatch-agent.d/file_amazon-cloudwatch-agent.json"
    }
    ->
    service { 'amazon-cloudwatch-agent':
      ensure => running,
      enable => true,
    }
  }
}
