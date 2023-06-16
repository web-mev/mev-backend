class mevapi::cloudwatch_agent () {

  if $mevapi::platform == 'aws' {

    $cloudwatch_agent_dir = '/opt/aws/amazon-cloudwatch-agent'

    file { '/tmp/amazon-cloudwatch-agent.deb':
        ensure => present,
        source => 'https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb',
        mode   => '0550',
        owner  => $app_user
    }

    file { '/tmp/amazon-cloudwatch-agent.deb.sig':
        ensure => present,
        source => 'https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb.sig',
        mode   => '0550',
        owner  => $app_user
    }

    package { 'amazon-cloudwatch-agent':
        provider => dpkg,
        source => '/tmp/amazon-cloudwatch-agent.deb'
    }
    ->
    file { "${cloudwatch_agent_dir}/etc/cloudwatch_config.json":
        ensure  => file,
        content => epp('mevapi/cloudwatch_config.json.epp'),
        owner   => $app_user,
        group   => $app_user,
    }
    ~>
    exec { 'cloudwatch_agent':
        command => "${cloudwatch_agent_dir}/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 \
        -c file:${cloudwatch_agent_dir}/etc/cloudwatch_config.json",
        creates => "${cloudwatch_agent_dir}/etc/amazon-cloudwatch-agent.d/file_cloudwatch_config.json"
    }
    ->
    service { 'amazon-cloudwatch-agent':
        ensure => running,
        enable => true,
    }
  }
  else {
      
  }

}