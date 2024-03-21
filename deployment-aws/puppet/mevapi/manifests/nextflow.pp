class mevapi::nextflow () {

    $nextflow_executable = "/opt/nextflow"

    exec { 'install_nextflow':
      cwd     => "/opt",
      command => "/usr/bin/curl -s https://get.nextflow.io | /bin/bash",
      creates => "${nextflow_executable}"
    }
    ~>
    file { $nextflow_executable:
        mode   => '0755'
    }
}
