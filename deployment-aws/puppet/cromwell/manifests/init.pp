# @summary Install and configure Cromwell workflow management system
#
# Provisions Cromwell with AWS Batch backend
#
# @example
#   include cromwell
class cromwell (
  String           $api_storage_bucket,
  String           $aws_region,
  String           $job_queue,
  String           $storage_bucket,
  Optional[String] $project_root,
) {
  $user = 'ubuntu'
  $log_dir = '/var/log/cromwell'
  $db_password = fqdn_rand_string(6)

  contain cromwell::install
  contain cromwell::config
  contain cromwell::service

  Class['cromwell::install'] -> Class['cromwell::config'] ~> Class['cromwell::service']
}
