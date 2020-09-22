import os
import json
import subprocess
import logging

from django.conf import settings
from django.utils.module_loading import import_string

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

    # A list of files that are required to be part of the repository
    REQUIRED_FILES = OperationRunner.REQUIRED_FILES + [
        os.path.join(OperationRunner.DOCKER_DIR, DOCKERFILE),
    ]

    # a mapping of strings to the class implementation for various converters
    CONVERTER_MAPPING = {

    }

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

        # get the operation dir so we can look at which converters to use:
        op_dir = os.path.join(
            settings.OPERATION_LIBRARY_DIR, 
            str(op_data['id'])
        )

        # get the file which states which converters to use:
        converter_file_path = os.path.join(op_dir, OperationRunner.CONVERTER_FILE)
        if not os.path.exists(converter_file_path):
            logger.error('Could not find the required converter file at {p}.'
                ' Something must have corrupted the operation directory.'.format(
                    p = converter_file_path
                )
            )
            raise Exception('The repository must have been corrupted.'
                ' Check dir at: {d}'.format(
                    d = op_dir
                )
            )
        converter_dict = json.load(open(converter_file_path))
        arg_dict = {}
        for k,v in validated_inputs.items():
            try:
                converter_class_str = converter_dict[k] # a string telling us which converter to use
                converter_class = import_string(converter_class_str)
            except KeyError as ex:
                logger.error('Could not locate a converter for input: {i}'.format(
                    i = k
                ))
                raise ex

            c = converter_class()
            arg_dict[k] = c.convert(v)

        logger.info('After mapping the user inputs, we have the'
            ' following structure: {d}'.format(d = arg_dict)
        )
