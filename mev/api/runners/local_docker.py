import os
import json
import datetime
import subprocess
import logging

from jinja2 import Template

from django.conf import settings
from django.utils.module_loading import import_string

from api.runners.base import OperationRunner
from api.utilities.operations import get_operation_instance_data
from api.utilities.docker import build_docker_image, \
    login_to_dockerhub, \
    push_image_to_dockerhub, \
    check_if_container_running, \
    check_container_exit_code, \
    get_finish_datetime, \
    remove_container
from api.data_structures.attributes import DataResourceAttribute
from api.utilities.basic_utils import make_local_directory, \
    copy_local_resource, \
    alert_admins, \
    run_shell_command
from api.models import ExecutedOperation
from api.converters.output_converters import LocalDockerOutputConverter

logger = logging.getLogger(__name__)

class LocalDockerRunner(OperationRunner):
    '''
    Class that handles execution of `Operation`s using Docker on the local
    machine
    '''
    MODE = 'local_docker'

    # the name of the Dockerfile which resides in the docker directory.
    # Used to build the Docker image
    DOCKERFILE = 'Dockerfile'

    # a file that specifies the entrypoint "command" that is run:
    ENTRYPOINT_FILE = 'entrypoint.txt'

    # A list of files that are required to be part of the repository
    REQUIRED_FILES = OperationRunner.REQUIRED_FILES + [
        os.path.join(OperationRunner.DOCKER_DIR, DOCKERFILE),
        ENTRYPOINT_FILE
    ]

    # the template docker command to be run:
    DOCKER_RUN_CMD = ('docker run -d --name {container_name}'
        ' -v {execution_mount}:/{work_dir} '
        '--entrypoint="" {username}/{image}:{tag} {cmd}')

    def check_status(self, job_uuid):
        container_is_running = check_if_container_running(job_uuid)
        if container_is_running:
            return False
        else:
            return True

    def load_outputs_file(self, job_id):
        execution_dir = os.path.join(
            settings.OPERATION_EXECUTION_DIR, job_id)

        # the outputs json file:
        outputs_dict = json.load(open(
            os.path.join(execution_dir, self.OUTPUTS_JSON)
        ))
        return outputs_dict

    def finalize(self, executed_op):
        '''
        Finishes up an ExecutedOperation. Does things like registering files 
        with a user, cleanup, etc.
        '''
        job_id = str(executed_op.job_id)
        exit_code = check_container_exit_code(job_id)
        finish_datetime = get_finish_datetime(job_id)
        executed_op.execution_stop_datetime = finish_datetime
        executed_op.is_finalizing = False # so future requests don't think it is still finalizing

        if exit_code != 0:
            executed_op.job_failed = True
            executed_op.status = ExecutedOperation.COMPLETION_ERROR
            #TODO: add some error message so the user can evaluate?
        else:
            executed_op.job_failed = False
            executed_op.status = ExecutedOperation.COMPLETION_SUCCESS
        
            # the outputs json file:
            outputs_dict = self.load_outputs_file(job_id)

            # the workspace so we know which workspace to associate outputs with:
            user_workspace = executed_op.workspace

            # get the operation spec so we know which types correspond to each output
            op_data = get_operation_instance_data(executed_op.operation)
            op_spec_outputs = op_data['outputs']

            # instantiate the output converter class:
            converter = LocalDockerOutputConverter()

            new_outputs_dict = {}
            for k,v in outputs_dict.items():
                try:
                    spec = op_spec_outputs[k]['spec']
                except KeyError as ex:
                    logger.error('Could not locate the output with key={k} in'
                        ' the outputs of operation with ID: {id}'.format(
                            k = k,
                            id = str(executed_op.operation.id)
                        )
                    )
                    alert_admins()
                else:
                    new_outputs_dict[k] = converter.convert_output(job_id, user_workspace, spec, v)
            executed_op.outputs = new_outputs_dict
        executed_op.save()

        # finally, we cleanup the docker container
        remove_container(job_id)

        return

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

    def _map_inputs(self, op_dir, validated_inputs):
        '''
        Takes the inputs (which are MEV-native data structures)
        and make them into something that we can pass to a command-line
        call. 

        For instance, this takes a DataResource (which is a UUID identifying
        the file), and turns it into a local path.
        '''
        converter_dict = self._get_converter_dict(op_dir)
        arg_dict = {}
        for k,v in validated_inputs.items():
            try:
                converter_class_str = converter_dict[k] # a string telling us which converter to use
            except KeyError as ex:
                logger.error('Could not locate a converter for input: {i}'.format(
                    i = k
                ))
                raise ex
            try:
                converter_class = import_string(converter_class_str)
            except Exception as ex:
                logger.error('Failed when importing the converter class: {clz}'
                    ' Exception was: {ex}'.format(
                        ex=ex,
                        clz = converter_class_str
                    )
                )
                raise ex
            # instantiate the converter and convert the arg:
            c = converter_class()
            arg_dict[k] = c.convert(v)

        return arg_dict

    def _copy_data_resources(self, execution_dir, op_data, arg_dict):
        '''
        Copies files (DataResource instances) from the user's local cache
        to a sandbox dir.

        `execution_dir` is where we want to copy the files
        `op_data` is the full operation "specification"
        `arg_dict` is the user inputs, which have already been
          mapped to appropriate commandline args
        '''
        for k,v in op_data['inputs'].items():
            # v has type of OperationInput
            spec = v['spec']
            attribute_type = spec['attribute_type']
            if attribute_type == DataResourceAttribute.typename:
                path_in_cache = arg_dict[k]
                dest = os.path.join(execution_dir, os.path.basename(path_in_cache))
                copy_local_resource(path_in_cache, dest)
                arg_dict[k] = dest

    def _get_entrypoint_command(self, entrypoint_file_path, arg_dict):
        '''
        Takes the entrypoint command file (a template) and the input
        args and returns a formatted string which will be used as the 
        ENTRYPOINT command for the Docker container.
        '''
        # read the template command
        entrypoint_cmd_template = Template(open(entrypoint_file_path, 'r').read())
        try:
            entrypoint_cmd = entrypoint_cmd_template.render(arg_dict)
            return entrypoint_cmd
        except Exception as ex:
            logger.error('An exception was raised when constructing the entrypoint'
                ' command from the templated string. Exception was: {ex}'.format(
                    ex = ex
                )
            )
            raise Exception('Failed to construct command to execute'
                ' local Docker container. See logs.'
            )

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

        # the UUID identifying the execution of this operation:
        execution_uuid = str(executed_op.id)

        # get the operation dir so we can look at which converters and command to use:
        op_dir = os.path.join(
            settings.OPERATION_LIBRARY_DIR, 
            str(op_data['id'])
        )

        # convert the user inputs into args compatible with commandline usage:
        arg_dict = self._map_inputs(op_dir, validated_inputs)

        # Note that any paths (i.e. DataResources) are currently in the user cache directory.
        # To avoid conflicts, we want to run each operation in its own sandbox, so we
        # copy over any DataResources to a new directory:
        execution_dir = os.path.join(settings.OPERATION_EXECUTION_DIR, execution_uuid)
        make_local_directory(execution_dir)
        self._copy_data_resources(execution_dir, op_data, arg_dict)

        logger.info('After mapping the user inputs, we have the'
            ' following structure: {d}'.format(d = arg_dict)
        )

        # Construct the command that will be run in the container:
        entrypoint_file_path = os.path.join(op_dir, self.ENTRYPOINT_FILE)
        if not os.path.exists(entrypoint_file_path):
            logger.error('Could not find the required entrypoint file at {p}.'
                ' Something must have corrupted the operation directory.'.format(
                    p = entrypoint_file_path
                )
            )
            raise Exception('The repository must have been corrupted.'
                ' Failed to find the entrypoint file.'
                ' Check dir at: {d}'.format(
                    d = op_dir
                )
            )
        entrypoint_cmd = self._get_entrypoint_command(entrypoint_file_path, arg_dict)

        cmd = self.DOCKER_RUN_CMD.format(
            container_name = execution_uuid,
            execution_mount = settings.EXECUTION_VOLUME,
            work_dir = settings.OPERATION_EXECUTION_DIR,
            cmd = entrypoint_cmd,
            username = settings.DOCKERHUB_USERNAME,
            image = op_data['repo_name'],
            tag = op_data['git_hash']
        )
        try:
            run_shell_command(cmd)
        except Exception as ex:
            # if an exception is raised when issuing the Docker run
            # command, then the job has failed. This error is likely
            # not due to user error, but something with the issuing
            # command or allocating appropriate Docker resources.
            executed_op.job_failed = True
            executed_op.execution_stop_datetime = datetime.datetime.now()
            executed_op.status = ExecutedOperation.ADMIN_NOTIFIED
            executed_op.save()
            alert_admins()