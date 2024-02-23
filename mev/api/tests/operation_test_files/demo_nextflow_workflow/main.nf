process run_pca {

    tag "Run principal component analysis"
    publishDir "${params.output_dir}/pca_results", mode:"copy"
    container "ghcr.io/web-mev/pca:sha-ede315244ea21f91be287b9504dbb71bc9ee3f2e"
    cpus 1
    memory '4 GB'

    input:
        path(input_file)

    output:
        path("pca_output.tsv")

    script:
        """
        python3 /usr/local/bin/run_pca.py -i ${input_file}
        """
}

process run_echo {

    tag "Some other process"
    publishDir "${params.output_dir}/echo_results", mode:"copy"
    container 'ghcr.io/web-mev/mev-hcl'
    cpus 1
    memory '2 GB'

    input:
        path(input_file)

    output:
        path("some_output.tsv")

    script:
        """
        cat ${input_file} > "some_output.tsv"
        """
}

process run_another_echo {

    tag "Yet another process"
    publishDir "${params.output_dir}/another_echo_results", mode:"copy"
    container 'docker.io/ubuntu:jammy'
    cpus 1
    memory '2 GB'

    input:
        path(input_file)

    output:
        path("some_output.tsv")

    script:
        """
        cat ${input_file} > "some_output.tsv"
        """
}

workflow {

    pca_ch = run_pca(params.nc)
    other_ch = run_echo(pca_ch)
    x_ch = run_another_echo(pca_ch)
}
