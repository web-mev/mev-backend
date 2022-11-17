class cromwell::cloudwatch_agent () {
    exec { 'cloudwatch_agent_start'
        command => "/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -s -c file:/etc/cloudwatch_agent_config.json"
        owner   => $cromwell::user,
        group   => $cromwell::user
    }
}