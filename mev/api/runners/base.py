import os
import json
import logging

from django.utils.module_loading import import_string

from api.utilities.operations import get_operation_instance_data
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

    # a JSON-format file which tells us which converter should be used to map
    # the user inputs to a format that the runner can understand/use
    CONVERTER_FILE = 'converters.json'

    # A list of files that are required to be part of the repository
    REQUIRED_FILES = [
        CONVERTER_FILE
    ]

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

        # check that the converters are viable:
        converter_dict = self._get_converter_dict(operation_dir)
        for k,v in converter_dict.items():
            try:
                import_string(v)
            except Exception as ex:
                logger.error('Failed when importing the converter class: {clz}'
                    ' Exception was: {ex}'.format(
                        ex=ex,
                        clz = v
                    )
                )
                raise ex

    def _get_converter_dict(self, op_dir):
        '''
        Returns the dictionary that gives the "converter" class strings. 
        Those strings give the classes which we use to map the 
        user-supplied inputs to an operation (of type UserOperationInput)
        to args appropriate for the specific runner. 
        '''
        # get the file which states which converters to use:
        converter_file_path = os.path.join(op_dir, self.CONVERTER_FILE)
        if not os.path.exists(converter_file_path):
            logger.error('Could not find the required converter file at {p}.'
                ' Something must have corrupted the operation directory.'.format(
                    p = converter_file_path
                )
            )
            raise Exception('The repository must have been corrupted.'
                ' Failed to find the argument converter file.'
                ' Check dir at: {d}'.format(
                    d = op_dir
                )
            )
        d = json.load(open(converter_file_path))
        logger.info('Read the following converter mapping: {d}'.format(d=d))
        return d

    def _map_inputs(self, op_dir, validated_inputs, staging_dir):
        '''
        Takes the inputs (which are MEV-native data structures)
        and make them into something that we can pass to a command-line
        call. 

        For instance, this might take a DataResource (which is a UUID identifying
        the file), and turns it into a local path. The actual mapping depends
        on the converter class defined by the Operation. Different operations
        might "transform" a Resource into different things (e.g. a path, a delimited
        string of the path and a resource type, etc.) depending on the requirements
        of the analysis.
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
            arg_dict.update(c.convert(k,v, op_dir, staging_dir))

        logger.info('After mapping the user inputs, we have the'
            ' following structure: {d}'.format(d = arg_dict)
        )
        return arg_dict

    def convert_outputs(self, executed_op, converter, outputs_dict):
        '''
        Handles the mapping from outputs (as provided by the runner)
        to MEV-compatible data structures or resources.
        '''

        # the workspace so we know which workspace to associate outputs with:
        user_workspace = getattr(executed_op, 'workspace', None)

        # get the operation spec so we know which types correspond to each output
        op_data = get_operation_instance_data(executed_op.operation)
        op_spec_outputs = op_data['outputs']

        converted_outputs_dict = {}
        try:
            # note that the sort is not necessary, but it incurs little penalty.
            # However, it does make unit testing easier.
            for k in sorted(op_spec_outputs.keys()):
                current_output = op_spec_outputs[k]
                try:
                    v = outputs_dict[k]
                except KeyError as ex:
                    error_msg = ('Could not locate the output with key={k} in'
                        ' the outputs of operation with ID: {id}'.format(
                            k = k,
                            id = str(executed_op.operation.id)
                        )
                    )
                    logger.info(error_msg)
                    alert_admins(error_msg)
                    raise OutputConversionException(error_msg)

                else:
                    if v is not None:
                        logger.info('Executed operation output was not None. Convert.')
                        converted_outputs_dict[k] = converter.convert_output(executed_op, user_workspace, current_output, v)
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
                error_msg = ('There were extra keys ({keys}) in the output of'
                    ' the operation. Check this.'.format(keys=','.join(extra_keys)))
                logger.info(error_msg)
                alert_admins(error_msg)

            return converted_outputs_dict
        except OutputConversionException as ex:
            logger.info('Requesting cleanup of an ExecutedOperation due to failure'
                ' while converting outputs.'
            )
            self.cleanup_on_error(op_spec_outputs, converted_outputs_dict)
            raise ex