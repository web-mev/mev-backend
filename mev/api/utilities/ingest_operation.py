import json
import os
import uuid
import logging
import subprocess as sp
import shutil
import requests

from django.conf import settings
from rest_framework.exceptions import ValidationError

from api.models import Operation as OperationDbModel
from api.models import OperationResource
from api.data_structures import OperationDataResourceAttribute
from api.serializers.operation import OperationSerializer
from api.utilities.basic_utils import recursive_copy
from api.utilities.operations import read_operation_json, \
    validate_operation, \
    resource_operations_file_is_valid
from api.utilities.resource_utilities import get_resource_size, \
    move_resource_to_final_location
from api.storage_backends.helpers import get_storage_implementation
from api.runners import get_runner
from api.exceptions import OperationResourceFileException

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
    cmd = 'git show -s --format=%H'
    logger.info('Retrieve git commit with: {cmd}'.format(
        cmd=cmd
    ))
    cmd = cmd.split(' ')

    p = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.STDOUT, cwd=git_dir)
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


def checkout_branch(git_dir, commit_id):
    '''
    Changes given a given git directory to the desired commit
    '''
    logger.info('Attempt to checkout commit {commit_id}'.format(commit_id=commit_id))
    cmd = 'git checkout {commit_id}'.format(
        git_dir=git_dir,
        commit_id = commit_id
    )
    logger.info('Checkout commit with: {cmd}'.format(
        cmd=cmd
    ))
    cmd = cmd.split(' ')

    p = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.STDOUT, cwd=git_dir)
    stdout, stderr = p.communicate()
    if p.returncode != 0:
        logger.error('Problem with checking out'
            ' commit {commit_id} from the git repo at {git_dir}.\n'
            'STDERR was: {stderr}\nSTDOUT was: {stdout}'.format(
                commit_id=commit_id,
                git_dir=git_dir,
                stderr=stderr,
                stdout=stdout
            )
        )
        raise Exception('Failed when attemping to checkout a particular commit. See logs.')
    else:
        commit_hash = stdout.strip().decode('utf-8')
        return commit_hash

def retrieve_repo_name(git_dir):
    '''
    Retrieves the git repository name given a directory
    '''
    logger.info('Retrieve git repo name')
    cmd = 'git remote get-url origin'.format(
        git_dir=git_dir
    )
    logger.info('Retrieve git repo name with: {cmd}'.format(
        cmd=cmd
    ))
    cmd = cmd.split(' ')

    p = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.STDOUT, cwd=git_dir)
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
        logger.info('Repo was found to be: {x}'.format(x=git_str))
        final_piece = git_str.split('/')[-1]
        if final_piece.endswith('.git'):
            return final_piece[:-4]
        else:
            return final_piece

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


def check_for_operation_resources(op_data):
    '''
    This function looks through the operation spec to check if there are any inputs
    that correspond to "static" operation resources (i.e. user-independent/operation-specific files)
    
    If yes, returns a dict which is a subset of the `inputs` object from the operation spec file.
    Only the inputs that correspond to operation resources are included. If none of the inputs
    are operation resources, then return an empty dict
    '''
    d = {}
    for input_key, op_input in op_data['inputs'].items():
        spec = op_input['spec']
        if spec['attribute_type'] == OperationDataResourceAttribute.typename:
            d[input_key] = op_input
    return d

def create_operation_resource(input_name, op_resource_dict, op_uuid, op_data, staging_dir):
    '''
    Takes the op_resource_dict (a dict with name, path) and creates a database
    instance of an OperationResource
    '''
    name = op_resource_dict['name']
    path = op_resource_dict['path']
    resource_type = op_resource_dict['resource_type']

    # check that the file actually exists. If the path has a prefix like "gs://"
    # then we know infer that it is stored in a google bucket. If it doesn't match
    # any specific "other" storage system (GCP bucket, AWS bucket, etc.) then we look
    # locally, RELATIVE to the staging directory
    storage_impl = get_storage_implementation(path)

    # if the resource file specifies it as local, then we need to look for the file
    # in the staging dir. If it was specified as a bucket URL, etc. then we don't need
    # to edit the path, since it should already be properly formed.
    if storage_impl.is_local_storage:
        path = os.path.join(staging_dir, path)
    exists = storage_impl.resource_exists(path)
    if not exists:
        raise OperationResourceFileException('Could not locate the operation resource'
            ' at {p}'.format(p=path)
        )

    # create the database object
    try:
        op = OperationDbModel.objects.get(pk=op_uuid)
    except OperationDbModel.DoesNotExist as ex:
        logger.info('Failed to find an Operation with UUID={u}.'.format(
            u = str(op_uuid)
        ))
        raise ex

    op_resource = OperationResource.objects.create(
        name = name,
        operation = op,
        path = path, 
        input_field = input_name,
        resource_type = resource_type
    )
    final_path = move_resource_to_final_location(op_resource)
    op_resource.path = final_path
    file_size = get_resource_size(op_resource)
    op_resource.size = file_size
    op_resource.save()

    # now that we have the final path, edit the location
    d = {
        'name': name,
        'path': final_path,
        'resource_type': resource_type
    }
    return d

def handle_operation_specific_resources(op_data, staging_dir, op_uuid):
    '''
    This function looks through the operation's inputs and handles any 
    operation-specific resources. These are user-independent resources (such as 
    genome indices) that are associated with an Operation, but are obviously 
    distinct from a user's files.
    '''

    # look through the inputs and see if any correspond to OperationDataResource.
    # If not, immediately return
    relevant_inputs = check_for_operation_resources(op_data)
    if not relevant_inputs:
        return

    # If here, one or more inputs were OperationDataResource. Need to check that they exist and 
    # move them to the proper location(s).

    # First check that the repo has the file giving the location of those OperationDataResources
    resource_file = os.path.join(staging_dir, OperationResource.OPERATION_RESOURCE_FILENAME)
    if not os.path.exists(resource_file):
        raise OperationResourceFileException('During ingestion, we could not find the file specifying'
            ' the operation resources at: {p}'.format(p=resource_file)
        )

    # read the file
    try:
        operation_resource_data = json.load(open(resource_file))
    except json.decoder.JSONDecodeError as ex:
        raise OperationResourceFileException('Could not use the JSON parser to load'
            ' the file at {p}. Exception was {ex}'.format(
                p=resource_file,
                ex = ex
        ))

    # file existed and was valid JSON. Now check that we have info for each of the inputs and 
    # that the JSON was in the format we expect:
    valid_format = resource_operations_file_is_valid(operation_resource_data, relevant_inputs.keys())
    if not valid_format:
        raise OperationResourceFileException('The operation resource file at {p} was not formatted'
            ' correctly.'.format(p=resource_file)
        )
    
    # iterate through the operation resources, creating database objects and updating
    # the spec to reflect the final resource locations.
    updated_dict = {}
    for k in relevant_inputs.keys():
        operation_resource_list = operation_resource_data[k]
        updated_list = []
        for item in operation_resource_list:
            updated_item = create_operation_resource(k, item, op_uuid, op_data, staging_dir)
            updated_list.append(updated_item)
        updated_dict[k] = updated_list
    # write this updated dict to the same file we read from:
    with open(resource_file, 'w') as fout:
        fout.write(json.dumps(updated_dict))

def prepare_operation(op_data, staging_dir, repo_name, git_hash):
    '''
    This function calls out to the runner to have it prepare the necessary
    elements to run the Operation.

    For instance, in a local Docker-based job, we need to build the container
    For a cromwell job, we need to build the containers and push to dockerhub
    '''
    run_mode = op_data['mode']
    runner_class = get_runner(run_mode)
    runner = runner_class()
    runner.prepare_operation(staging_dir, repo_name, git_hash)


def check_for_repo(repository_url):
    '''
    This function checks that we can reach a particular repository.

    If a bad url is given, the GET request will return 404. This is different
    than the behavior with a `git clone` where a bad repo url will first
    attempt to log you in via the terminal (which requires interactivity or
    storing github keys). Recall that we will only work with public repos
    anyway.
    '''
    r = requests.get(repository_url)
    if r.status_code == 200:
        return
    else:
        raise Exception('Could not find the repository'
            ' at {r} or it was not public'.format(r=repository_url))

def perform_operation_ingestion(repository_url, op_uuid, commit_id):
    '''
    This function is the main entrypoint for the ingestion of a new `Operation`
    '''

    # Check that we can find this
    check_for_repo(repository_url)

    # pull from the repository:
    staging_dir = clone_repository(repository_url)

    if commit_id:
        # if provided with a commit ID, check that out
        checkout_branch(staging_dir, commit_id)
        git_hash = commit_id
    else:
        git_hash = retrieve_commit_hash(staging_dir)
        
    repo_name = retrieve_repo_name(staging_dir)
    try:
        ingest_dir(staging_dir, op_uuid, git_hash, repo_name, repository_url)
    except Exception as ex:
        logger.info('Failed to ingest directory. See logs.'
            ' Exception was: {ex}'.format(ex=ex)
        )
        raise ex
    finally:
        # remove the staging dir:
        shutil.rmtree(staging_dir)

def ingest_dir(staging_dir, op_uuid, git_hash, repo_name, repository_url, overwrite=False):

    # Parse the JSON file defining this new Operation:
    operation_json_filepath = os.path.join(staging_dir, settings.OPERATION_SPEC_FILENAME)
    j = read_operation_json(operation_json_filepath)

    # extra parameters for an Operation that are not required
    # to be specified by the developer who wrote the `Operation`
    add_required_keys_to_operation(j, id=op_uuid,
        git_hash = git_hash,
        repository_url = repository_url,
        repo_name = repo_name
    )

    # attempt to validate the data for the operation:
    try:
        op_serializer = validate_operation(j)
    except ValidationError as ex:
        logger.info('A validation error was raised when validating'
            ' the information parsed from {path}. Exception was: {ex}.\n '
            'Full info was: {j}'.format(
                path = operation_json_filepath,
                j = json.dumps(j, indent=2),
                ex = ex
            )
        )
        raise ex
    except Exception as ex:
        logger.info('An unexpected error was raised when validating'
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
    op_data = op.to_dict()
    #op_data = OperationSerializer(op).data
    logging.info('After parsing operation spec, we have: {spec}'.format(spec=op_data))

    # check that the required files, etc. are there for the particular run mode:
    check_required_files(op_data, staging_dir)

    # handle any operation-specific resources/files:
    handle_operation_specific_resources(op_data, staging_dir, op_uuid)

    # prepare any elements required for running the operation:
    prepare_operation(op_data, staging_dir, repo_name, git_hash)

    # save the operation in a final location:
    save_operation(op_data, staging_dir, overwrite)

    # update the database instance.
    try:
        o = OperationDbModel.objects.get(id=op.id)
        o.name = op.name
        o.active = True
        o.successful_ingestion = True
        o.workspace_operation = op_data['workspace_operation']
        o.save()
    except OperationDbModel.DoesNotExist:
        logger.error('Could not find the Operation corresponding to'
            ' id={u}'.format(u=op_uuid)
        )
        raise Exception('Encountered issue when trying update an Operation'
            ' database instance after ingesting from repository.'
        )

def save_operation(op_data, staging_dir, overwrite):
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
    recursive_copy(staging_dir, dest_dir, include_hidden=True, overwrite=overwrite)

    # overwrite the spec file just to ensure it's valid with our 
    # current serializer implementation. Technically it wouldn't validate
    # if that weren't true, but we do it here either way.
    op_fileout = os.path.join(dest_dir, settings.OPERATION_SPEC_FILENAME)
    with open(op_fileout, 'w') as fout:
        fout.write(json.dumps(op_data))