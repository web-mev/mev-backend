workflow AWSDropboxUpload {

    # This upload process works by using the dropbox
    # url to download the file onto the machine. That
    # local path is then reported as an output `File`
    # so that Cromwell picks it up and puts it in the Cromwell
    # associated bucket. From there, WebMeV knows how to 
    # transfer it to WebMeV-associated storage.
    # This avoids having to provide worker machines with the 
    # policies/roles needed to both download and 
    # subsequently push directly to the WebMeV bucket.

    # The dropbox URL
    String dropbox_link
    
    # the name of the file as it was in their dropbox 
    String filename

    call upload {
        input:
            link = dropbox_link,
            fname = filename
    }

    output {
        File uploaded_file = upload.fout
    }
}

task upload {

    String link
    String fname

    Int disk_size = 200

    command {
        wget -q -O ${fname} ${link}
    }

    output {
        String fout = ${fname}
    }

    runtime {
        docker: "ghcr.io/web-mev/aws_bucket_dropbox_upload"
        cpu: 1
        memory: "4 G"
        disks: "local-disk " + disk_size + " HDD"
        preemptible: 0
    }
}
