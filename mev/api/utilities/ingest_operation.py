import json
import os
import uuid
import logging
import subprocess as sp
import shutil

from django.conf import settings
from rest_framework.exceptions import ValidationError

from api.models import Operation as OperationDbModel
from api.serializers.operation import OperationSerializer
from api.utilities.basic_utils import recursive_copy
from api.utilities.operations import read_operation_json, \
    validate_operation
from api.runners import get_runner

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
    cmd = 'git --git-dir {git_dir}/.git show -s --format=%H'.format(
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

def retrieve_repo_name(git_dir):
    '''
    Retrieves the git repository name given a directory
    '''
    logger.info('Retrieve git repo name')
    cmd = 'git --git-dir {git_dir}/.git remote get-url origin'.format(
        git_dir=git_dir
    )
    logger.info('Retrieve git repo name with: {cmd}'.format(
        cmd=cmd
    ))
    cmd = cmd.split(' ')

    p = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.STDOUT)
    stdout, stderr = p.communicate()
    if p.returncode != 0:
        logger.error('Problem with querying the'
            ' repo name from the git repo at {git_dir}.\n'
            'STDERR was: {stderr}\nSTDOUT was: {stdout}'.format(
                git_dir=git_dir,
                stderr=stderr,
                stdout=stdout
            )
        )
        raise Exception('Failed when querying the git commit ID. See logs.')
    else:
        git_str = stdout.strip().decode('utf-8')
        name = git_str.split('/')[-1][:-4]
        return name

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
    
def check_required_files(op_data, staging_dir):
    '''
    Depending on how an Operation is run (local, cromwell), we have different
    requirements for the files needed.
    '''
    run_mode = op_data['mode']
    runner_class = get_runner(run_mode)
    runner = runner_class()
    runner.check_required_files(staging_dir)


def perform_operation_ingestion(repository_url, op_uuid):
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
    add_required_keys_to_operation(j, id=op_uuid,
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

    # get an instance of the Operation (the data structure, NOT the database model)
    op = op_serializer.get_instance()
    op_data = OperationSerializer(op).data

    # check that the required files, etc. are there for the particular run mode:
    check_required_files(op_data, staging_dir)

    # save the operation in a final location:
    save_operation(op_data, staging_dir)

    # update the database instance.
    try:
        o = OperationDbModel.objects.get(id=op.id)
        o.name = op.name
        o.active = True
        o.successful_ingestion = True
        o.save()
    except OperationDbModel.DoesNotExist:
        logger.error('Could not find the Operation corresponding to'
            ' id={u}'.format(u=op_uuid)
        )
        raise Exception('Encountered issue when trying update an Operation'
            ' database instance after ingesting from repository.'
        )

    # remove the staging dir:
    shutil.rmtree(staging_dir)

def save_operation(op_data, staging_dir):
    logger.info('Save the operation')
    op_uuid = op_data['id']
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
        fout.write(json.dumps(op_data))