# @summary Install and configure Cromwell workflow management system
#
# Provisions Cromwell with AWS Batch backend
#
# @example
#   include cromwell
class cromwell (
  Optional[String] $api_storage_bucket,
  Optional[String] $aws_region,
  Optional[String] $cloudwatch_log_group,
  Optional[String] $job_queue,
  Optional[String] $storage_bucket,
) {
  if $facts['virtual'] == 'kvm' {
    $platform = 'aws'
  } else {
    # VirtualBox
    $platform = $facts['virtual']
  }
  $user = 'ubuntu'
  $log_dir = '/var/log/cromwell'
  $db_password = fqdn_rand_string(6)
  $cloudwatch_agent_dir = '/opt/aws/amazon-cloudwatch-agent'

  contain cromwell::install
  contain cromwell::config
  contain cromwell::service

  Class['cromwell::install']
  ->
  Class['cromwell::config']
  ~>
  Class['cromwell::service']
}
