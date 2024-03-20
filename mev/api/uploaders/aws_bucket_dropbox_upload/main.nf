process run_download {

    tag "Download file"
    publishDir "${params.output_dir}/AWSDropboxUpload.uploaded_file", mode:"copy", pattern:"${fname}"
    container "ghcr.io/web-mev/aws_bucket_dropbox_upload"
    cpus 1
    memory '2 GB'

    input:
        val dropbox_link
        val fname

    output:
        path("${fname}")

    script:
        """
        wget -q -O ${fname} ${dropbox_link}
        """
}

workflow {
    run_download(params.dropbox_link, params.filename)
}