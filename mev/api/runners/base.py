import os
import logging

from django.utils.module_loading import import_string

from api.utilities.admin_utils import alert_admins
from api.exceptions import OutputConversionException

logger = logging.getLogger(__name__)


class MissingRequiredFileException(Exception):
    pass


class OperationRunner(object):
    '''
    A base class for classes which handle the execution of jobs/operations
    '''

    # the name of the folder (relative to the repository) which has the docker
    # context
    DOCKER_DIR = 'docker'

    # A list of files that are required to be part of the repository.
    # Derived classes can add to this for their specific needs
    REQUIRED_FILES = []

    # the name of the file which will direct us to the outputs from an ExecutedOperation.
    # It will be placed in the execution directory by the job
    OUTPUTS_JSON = 'outputs.json'

    def check_if_ready(self):
        '''
        This is called on startup to see if a particular implementation
        of a runner is indeed ready to run. Examples include checking that
        the Cromwell server is online, etc.

        This will typically be overridden by a child class. If not, then
        it will assume it's ready (by not raising an exception)
        '''
        pass


    def prepare_operation(self, operation_dir, repo_name, git_hash):
        '''
        Used during ingestion to perform setup/prep before an operation can 
        be executed. Use for things like building docker images, etc.

        Typically, the subclasses will implement something specific to their 
        execution mode.
        '''
        pass

    def check_required_files(self, operation_dir):
        '''
        Checks that the files required for a particular run mode are, in fact,
        in the directory.

        `operation_dir` is a path (local) to a directory containing the files
        defining the Operation
        '''
        logger.info('Checking required files are present in the respository')
        for f in self.REQUIRED_FILES:
            expected_path = os.path.join(operation_dir, f)
            logging.info('Look for: {p}'.format(p=expected_path))
            if not os.path.exists(expected_path):
                logging.info('Could not find the required file: {p}'.format(p=expected_path))
                raise MissingRequiredFileException('Could not locate the'
                    ' required file ({f}) in the repository at {d}'.format(
                        f=f,
                        d=operation_dir
                    )
                )
        logger.info('Done checking for required files.')


    def _get_converter(self, converter_class_str):
        try:
            converter_class = import_string(converter_class_str)
            return converter_class()
        except Exception as ex:
            logger.error('Failed when importing the converter class: {clz}'
                ' Exception was: {ex}'.format(
                    ex=ex,
                    clz = converter_class_str
                )
            )
            raise ex  


    def _convert_inputs(self, op, op_dir, validated_inputs, staging_dir):
        '''
        Takes the inputs (which are MEV-native data structures)
        and make them into something that we can pass to a command-line
        call. 

        Note that `op` is an instance of data_structures.operation.Operation

        For instance, this might take a DataResource (which is a UUID identifying
        the file), and turns it into a local path. The actual mapping depends
        on the converter class defined by the Operation. Different operations
        might "transform" a Resource into different things (e.g. a path, a delimited
        string of the path and a resource type, etc.) depending on the requirements
        of the analysis.
        '''
        arg_dict = {}
        for k,v in validated_inputs.items():
            op_input = op.inputs[k]
            # instantiate the converter and convert the arg:
            converter = self._get_converter(op_input.converter)
            arg_dict[k] = converter.convert_input(v, op_dir, staging_dir)

        logger.info('After mapping the user inputs, we have the'
            f' following structure: {arg_dict}')
        return arg_dict


    def _convert_outputs(self, executed_op, op, outputs_dict):
        '''
        Handles the mapping from outputs (as provided by the runner)
        to MEV-compatible data structures or resources.
        '''

        # the workspace so we know which workspace to associate outputs with:
        user_workspace = getattr(executed_op, 'workspace', None)

        # get the operation spec so we know which types
        # correspond to each output
        op_spec_outputs = op.outputs

        converted_outputs_dict = {}
        try:
            # note that the sort is not necessary, but it incurs little penalty.
            # However, it does make unit testing easier.
            for k in sorted(op_spec_outputs.keys()):
                current_output_spec = op_spec_outputs[k]
                try:
                    v = outputs_dict[k]
                except KeyError as ex:
                    error_msg = (f'Could not locate the output with key={k}'
                        ' in the outputs of executed operation with ID:'
                        f' {executed_op.id}'
                    )
                    logger.info(error_msg)
                    alert_admins(error_msg)
                    raise OutputConversionException(error_msg)

                else:
                    if v is not None:
                        converter = self._get_converter(
                            current_output_spec.converter)
                        converted_outputs_dict[k] = converter.convert_output(
                            executed_op, user_workspace, current_output_spec, v)
                    else:
                        logger.info('Executed operation output was null/None.')
                        converted_outputs_dict[k] = None

            # If here, we had all the required output keys and they converted properly.
            # However, the analysis might have specified EXTRA outputs. This isn't necessarily
            # an error, but we treat it as such since it's clear there is a discrepancy between
            # the "spec" and the actual output. 
            # We don't fail the job, but we alert the admins.
            extra_keys = set(outputs_dict.keys()).difference(op_spec_outputs.keys())
            if len(extra_keys) > 0:
                error_msg = (f'There were extra keys ({",".join(extra_keys)})'
                    ' in the output of the operation. Check this.')
                logger.info(error_msg)
                alert_admins(error_msg)

            return converted_outputs_dict
        except OutputConversionException as ex:
            logger.info('Requesting cleanup of an ExecutedOperation due to failure'
                ' while converting outputs.'
            )
            self.cleanup_on_error(op_spec_outputs, converted_outputs_dict)
            raise ex