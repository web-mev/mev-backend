import json
import os
import uuid
import logging

from django.conf import settings
from rest_framework.exceptions import ValidationError

from api.serializers.operation import OperationSerializer
from api.utilities.basic_utils import read_local_file, \
    make_local_directory

logger = logging.getLogger(__name__)

def add_required_keys_to_operation(op_dict, **kwargs):
    '''
    When an analysis developer creates an Operation suitable for MEV, they
    do not have to specify keys like `id`, which is a unique UUID only used
    internally. However, they are necessary to create a properly
    functioning `Operation` instance.
    This function checks for those keys and adds them.
    '''
    op_dict.update(kwargs)

def clone_repository(repository_url):
    '''
    Clones the repository and returns the path to the stageing directory
    and git commit hash
    '''
    return ('','')

def perform_operation_ingestion(repository_url):
    '''
    This function is the main entrypoint for the ingestion of a new `Operation`
    '''
    # pull from the repository:
    #TODO: write this. need to pull files AND get the hash
    staging_dir, git_hash = clone_repository(repository_url)

    # Parse the JSON file defining this new Operation:
    #TODO: get the json spec file path
    operation_json_filepath = os.path.join(staging_dir, settings.OPERATION_SPEC_FILENAME)
    j = read_operation_json(operation_json_filepath)

    # extra parameters for an Operation that are not required
    # to be specified by the developer who wrote the `Operation`
    add_required_keys_to_operation(j, id=str(uuid.uuid4()),
        git_hash = git_hash,
        repository_url = repository_url
    )

    # attempt to validate the data for the operation:
    try:
        op_serializer = validate_operation(j)
    except ValidationError as ex:
        logging.error('A validation error was raised when validating'
            ' the information parsed from {path}. Exception was: {ex}.\n '
            'Full info was: {j}'.format(
                path = operation_json_filepath,
                j = json.dumps(j, indent=2),
                ex = ex
            )
        )
    except Exception as ex:
        logging.error('An unexpected error was raised when validating'
            ' the information parsed from {path}. Exception was: {ex}.\n '
            'Full info was: {j}'.format(
                path = operation_json_filepath,
                j = json.dumps(j, indent=2),
                ex = ex
            )
        )

    # save the operation in a final location:
    op = op_serializer.get_instance()
    save_operation(op)

def save_operation(operation_instance):
    logger.info('Save the operation')
    data = OperationSerializer(operation_instance).data
    op_uuid = data['id']
    dest_dir = os.path.join(
        settings.OPERATION_LIBRARY_DIR,
        op_uuid
    )
    make_local_directory(dest_dir)

    #TODO: copy other files

    op_fileout = os.path.join(dest_dir, settings.OPERATION_SPEC_FILENAME)
    with open(op_fileout, 'w') as fout:
        fout.write(json.dumps(data))


def read_operation_json(filepath):
    '''
    Performs ingestion of a JSON-format file defining an `Operation`

    Accepts a local filepath for the JSON file, returns a dict
    '''
    try:
        logger.info('Parse Operation definition file at {path}'.format(
            path=filepath
        ))
        fp = read_local_file(filepath)
        j = json.load(fp)
        fp.close()
        logger.info('Done reading file.')
        return j
    except Exception as ex:
        logger.error('Could not read the operation JSON-format file at {path}.'
            ' Exception was {ex}'.format(
                path = filepath,
                ex = ex
            )
        )

def validate_operation(operation_dict):
    '''
    Takes a dictionary and validates it against the definition
    of an `Operation`. Returns an instance of an `OperationSerializer`.
    '''
    logger.info('Validate the dictionary against the definition'
    ' of an Operation...')
    print('X'*40)
    print(operation_dict)
    print('X'*40)
    op_serializer = OperationSerializer(data=operation_dict)
    op_serializer.is_valid(raise_exception=True)
    return op_serializer