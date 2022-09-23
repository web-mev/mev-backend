# @summary Install and configure Cromwell workflow management system
#
# Provisions Cromwell with AWS Batch backend
#
# @example
#   include cromwell
class cromwell (
  Optional[String] $api_storage_bucket,
  Optional[String] $aws_region,
  Optional[String] $job_queue,
  Optional[String] $storage_bucket,
) {
  $user = 'ubuntu'
  $log_dir = '/var/log/cromwell'
  $db_password = fqdn_rand_string(6)

  contain cromwell::install
  contain cromwell::config
  contain cromwell::service

  Class['cromwell::install'] -> Class['cromwell::config'] ~> Class['cromwell::service']
}
