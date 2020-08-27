import json
import os
import uuid
import logging
import subprocess as sp

from django.conf import settings
from rest_framework.exceptions import ValidationError

from api.models import Operation as OperationDbModel
from api.serializers.operation import OperationSerializer
from api.utilities.basic_utils import read_local_file, \
    make_local_directory, \
    recursive_copy

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

def retrieve_commit_hash(git_dir):
    '''
    Retrieves the git commit ID given a directory
    '''
    logger.info('Retrieve commit ID.')
    cmd = 'git --git-dir {git_dir}/.git show -s --format=%%H'.format(
        git_dir=git_dir
    )
    logger.info('Retrieve git commit with: {cmd}'.format(
        cmd=cmd
    ))
    cmd = cmd.split(' ')

    p = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.STDOUT)
    stdout, stderr = p.communicate()
    if p.returncode != 0:
        logger.error('Problem with querying the'
            ' commit hash from the git repo at {git_dir}.\n'
            'STDERR was: {stderr}\nSTDOUT was: {stdout}'.format(
                git_dir=git_dir,
                stderr=stderr,
                stdout=stdout
            )
        )
        raise Exception('Failed when querying the git commit ID. See logs.')
    else:
        commit_hash = stdout.strip().decode('utf-8')
        return commit_hash

def clone_repository(url):
    '''
    This clones the repository and returns the destination dir
    '''
    uuid_str = str(uuid.uuid4())
    dest = os.path.join(settings.CLONE_STAGING_DIR, uuid_str)
    clone_cmd = 'git clone %s %s' % (url, dest)
    clone_cmd = clone_cmd.split(' ')
    logger.info('About to clone repository with command: {cmd}'.format(
        cmd = clone_cmd
    ))
    p = sp.Popen(clone_cmd, stdout=sp.PIPE, stderr=sp.STDOUT)
    stdout, stderr = p.communicate()

    if p.returncode != 0:
        logger.error('Problem when cloning the repository.\n'
            ' STDERR was: {stderr}\n'
            ' STDOUT was: {stdout}'.format(
                stderr=stderr,
                stdout=stdout
            )
        )
        raise Exception('Failed when cloning the repository. See logs.')
    logger.info('Completed clone.')
    return dest
    
def perform_operation_ingestion(repository_url):
    '''
    This function is the main entrypoint for the ingestion of a new `Operation`
    '''
    # pull from the repository:
    staging_dir = clone_repository(repository_url)
    git_hash = retrieve_commit_hash(staging_dir)

    # Parse the JSON file defining this new Operation:
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
        logger.error('A validation error was raised when validating'
            ' the information parsed from {path}. Exception was: {ex}.\n '
            'Full info was: {j}'.format(
                path = operation_json_filepath,
                j = json.dumps(j, indent=2),
                ex = ex
            )
        )
        raise ex
    except Exception as ex:
        logger.error('An unexpected error was raised when validating'
            ' the information parsed from {path}. Exception was: {ex}.\n '
            'Full info was: {j}'.format(
                path = operation_json_filepath,
                j = json.dumps(j, indent=2),
                ex = ex
            )
        )
        raise ex

    # save the operation in a final location:
    op = op_serializer.get_instance()
    save_operation(op, staging_dir)

    # create a database instance so we don't pick up other 'junk'
    # that may end up in the operations directory
    OperationDbModel.objects.create(id=op.id, name=op.name)

def save_operation(operation_instance, staging_dir):
    logger.info('Save the operation')
    data = OperationSerializer(operation_instance).data
    op_uuid = data['id']
    dest_dir = os.path.join(
        settings.OPERATION_LIBRARY_DIR,
        op_uuid
    )
    logger.info('Destination directory for'
        ' this operation at {p}'.format(p=dest_dir))

    # copy the cloned directory and include the .git folder
    # and any other hidden files/dirs:
    recursive_copy(staging_dir, dest_dir, include_hidden=True)

    # overwrite the spec file just to ensure it's valid with our 
    # current serializer implementation. Technically it wouldn't validate
    # if that weren't true, but we do it here either way.
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
    op_serializer = OperationSerializer(data=operation_dict)
    op_serializer.is_valid(raise_exception=True)
    return op_serializer