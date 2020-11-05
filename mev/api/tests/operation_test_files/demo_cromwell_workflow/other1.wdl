task task1 {

    String s

    Int disk_size = 100

    command {

    }

    output {

    }

    runtime {
        docker: "docker.io/someUser/myImg:v0.0.2"
        cpu: 2
        memory: "4 G"
        disks: "local-disk " + disk_size + " HDD"
        preemptible: 0
    }
}

task task1_A {

    String s

    Int disk_size = 100

    command {

    }

    output {

    }

    runtime {
        docker: "docker.io/someUser/someImg"
        cpu: 2
        memory: "4 G"
        disks: "local-disk " + disk_size + " HDD"
        preemptible: 0
    }
}
