import glob
import os
import re
import logging

NF_SUFFIX = '.nf'

logger = logging.getLogger(__name__)


def get_container_names(operation_dir):
    '''
    Given a directory containing nextflow files, 
    look through those files and grab all the container
    declarations.

    Return a list of those images
    '''
    image_set = set()
    for nf_text in get_nextflow_file_contents(operation_dir).values():
        intermediate_image_set = extract_process_containers(nf_text)
        image_set = image_set.union(intermediate_image_set)
    return list(image_set)


def get_nextflow_file_contents(operation_dir):
    '''
    Finds all nextflow files in `operation_dir` and
    returns a list where each item of the list is a string
    with the file content.

    While this function seems relatively trivial, it made unit
    testing easier for other functions.
    '''
    nf_files = glob.glob(os.path.join(operation_dir, '*' + NF_SUFFIX))
    contents = {}
    for nf_file in nf_files:
        contents[os.path.basename(nf_file)] = open(nf_file, 'r').read()
    return contents


def extract_process_containers(nf_text):
    '''
    Given a string containing the nextflow script, 
    return a set of containers (a string declaring
    the container name and possibly a tag).
    '''
    # nextflow scripts have lines like:
    # container "docker.io/foo"
    # and the syntax requires they are on one line so
    # the following regex will grab the entire line:
    containers = re.findall('container\s+.*', nf_text)
    logger.info('From NF file, parsed the following container'
        f' definitions: {containers}')
    container_set = set()
    for c in containers:
        # c is like: container "docker.io/foo"
        # with either single or double quote possible
        match = re.search('[\'\"].*[\'\"]', c)
        start, end = match.span()
        container_id = c[start:end][1:-1]
        container_set.add(container_id)
    return container_set


def edit_nf_containers(operation_dir, name_mapping):
    '''
    `operation_dir` is a folder where all the workflow files reside
    `name_mapping` is a dict that maps the original container runtimes
    to the new names (which have the proper tagging)
    '''
    for nf_file, nf_text in get_nextflow_file_contents(operation_dir).items():
        for orig_image_str, new_image_str in name_mapping.items():
            nf_text = re.sub(orig_image_str, new_image_str, nf_text)
        with open(os.path.join(operation_dir, nf_file), 'w') as fout:
            fout.write(nf_text)