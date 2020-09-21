import os
import subprocess
import logging

from django.conf import settings

from api.runners.base import OperationRunner
from api.utilities.operations import get_operation_instance_data
from api.utilities.docker import build_docker_image, \
    login_to_dockerhub, \
    push_image_to_dockerhub

logger = logging.getLogger(__name__)
class LocalDockerRunner(OperationRunner):
    '''
    Class that handles execution of `Operation`s using Docker on the local
    machine
    '''
    MODE = 'local_docker'

    DOCKERFILE = 'Dockerfile'
    INPUT_TRANSLATION_SCRIPT = 'translate_inputs.py'

    # A list of files that are required to be part of the repository
    REQUIRED_FILES = [
        os.path.join(OperationRunner.DOCKER_DIR, DOCKERFILE),
        INPUT_TRANSLATION_SCRIPT
    ]

    def prepare_operation(self, operation_dir, repo_name, git_hash):
        '''
        Prepares the Operation, including building and pushing the Docker container

        `operation_dir` is the directory where the staged repository is held
        `repo_name` is the name of the repository. Used for the Docker image name
        `git_hash` is the commit hash and it allows us to version the docker container
            the same as the git repository
        '''
        build_docker_image(repo_name, 
            git_hash, 
            os.path.join(operation_dir, self.DOCKER_DIR, self.DOCKERFILE), 
            os.path.join(operation_dir, self.DOCKER_DIR)
        )
        login_to_dockerhub()
        push_image_to_dockerhub(repo_name, git_hash)

    def run(self, executed_op, op_data, validated_inputs):
        logger.info('Running in local Docker mode.')
        logger.info('Executed op type: %s' % type(executed_op))
        logger.info('Executed op ID: %s' % str(executed_op.id))
        logger.info('Op data: %s' % op_data)
        logger.info(validated_inputs)

        # have to translate the user-submitted inputs to those that
        # the local docker runner can work with.
        # For instance, a differential gene expression requires one to specify
        # the samples that are in each group-- to do this, the Operation requires
        # two ObservationSet instances are submitted as arguments. The "translator"
        # will take the ObservationSet data structures and turn them into something
        # that the call with use- e.g. making a CSV list to submit as one of the args
        # like:
        # docker run <image> run_something.R -a sampleA,sampleB -b sampleC,sampleD
