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
  $user = 'ubuntu'
  $log_dir = '/var/log/cromwell'
  $db_password = fqdn_rand_string(6)

  contain cromwell::install
  contain cromwell::config
  contain cromwell::service
  contain cromwell::cloudwatch_agent

  Class['cromwell::install']
  ->
  Class['cromwell::config']
  ~>
  Class['cromwell::service']
  ~>
  Class['cromwell::cloudwatch_agent']
}
