class mevapi::nextflow () {

    $nextflow_dir = '/opt/nextflow'
    $nextflow_executable = "${nextflow_dir}/nextflow"

    file { $nextflow_dir:
        ensure => directory,
        owner  => $mevapi::app_user,
        group  => $mevapi::app_group
    }
    ~>
    exec { 'install_nextflow':
      cwd     => $nextflow_dir,
      command => "/usr/bin/curl -s https://get.nextflow.io | /bin/bash",
      creates => "${nextflow_executable}"
    }
    ~>
    file { $nextflow_executable:
        mode   => '0755'
    }
}
