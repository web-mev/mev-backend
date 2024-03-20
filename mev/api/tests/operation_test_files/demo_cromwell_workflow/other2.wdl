task task2 {

    String s

    Int disk_size = 100

    command {

    }

    output {

    }

    runtime {
        docker: "docker.io/someUser/anotherImg"
        cpu: 2
        memory: "4 G"
        disks: "local-disk " + disk_size + " HDD"
        preemptible: 0
    }
}
