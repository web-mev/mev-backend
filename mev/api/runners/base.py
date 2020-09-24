import os
import json
import logging

from django.utils.module_loading import import_string

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
