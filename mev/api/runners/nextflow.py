import logging

from api.runners.base import OperationRunner
from api.utilities.nextflow_utils import get_container_names, \
    edit_nf_containers
from api.utilities.docker import check_image_exists, \
    check_image_name_validity

logger = logging.getLogger(__name__)


class NextflowRunner(OperationRunner):
    '''
    Handles execution of `Operation`s using Nextflow
    '''

    MAIN_NF = 'main.nf'
    NF_INPUTS = 'params.json'
    RUN_CMD = '{NEXTFLOW_EXE} -bg run {main_nf} -c {config}' \
              ' -params-file {params} --output_dir {output_dir}' \
              ' -with-weblog {status_update_url} >{stdout} 2>{stderr}'

    # A list of files that are required to be part of the repository
    REQUIRED_FILES = OperationRunner.REQUIRED_FILES + [
        # the nf script
        MAIN_NF,
        # the input json file, as a template
        NF_INPUTS
    ]


class AWSBatchNextflowRunner(NextflowRunner):
    '''
    Implementation of the NextflowRunner that interfaces with
    AWS Batch
    '''
    NAME = 'nf_batch'

    def prepare_operation(self, operation_dir, repo_name, git_hash):

        container_image_names = get_container_names(operation_dir)
        logger.info('Found the following image names among the'
            f' Nextflow files: {", ".join(container_image_names)}')

        name_mapping = {}
        for full_image_name in container_image_names:
            final_image_name = check_image_name_validity(full_image_name,
                repo_name,
                git_hash)
            image_found = check_image_exists(final_image_name)
            if not image_found:
                raise Exception('Could not locate the following'
                    f' image: {final_image_name}. Aborting')

            # keep track of any "edited" image names so we can modify
            # the Nextflow files
            name_mapping[full_image_name] = final_image_name

        # change the name of the image in the NF file(s), saving them in-place:
        edit_nf_containers(operation_dir, name_mapping)