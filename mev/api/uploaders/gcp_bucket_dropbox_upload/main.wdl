workflow GCPDropboxUpload {

    # The dropbox URL
    String dropbox_link
    
    # the name of the file as it was in their dropbox 
    String filename

    # the name of the bucket (no gs:// prefix) where the files
    # will be sent to. Not necessarily the bucket where MEV normally deposits
    # its files
    String bucketname

    # the root where we will store the file, relative to the bucket.
    # For example, if this arg is "foo", then the file(s) will be stored in
    # gs://<bucket name>/foo/
    # Optional, as the script should supply a default
    String storage_root

    call upload {
        input:
            link = dropbox_link,
            fname = filename,
            bucketname = bucketname,
            storage_root = storage_root
    }

    output {
        String uploaded_path = upload.out
    }
}

task upload {

    String link
    String fname
    String bucketname
    String storage_root

    Int disk_size = 200

    command {
        python3 /opt/software/upload.py -s ${link} -n ${fname} -d ${bucketname} -r ${storage_root}
    }

    output {
        String out = read_string(stdout())
    }

    runtime {
        docker: "blawney/gcp_dropbox_upload"
        cpu: 1
        memory: "4 G"
        disks: "local-disk " + disk_size + " HDD"
        preemptible: 0
    }
}
