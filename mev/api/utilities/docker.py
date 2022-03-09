import datetime
import logging

from django.conf import settings

from api.utilities.basic_utils import run_shell_command
from api.container_registries import get_container_registry, infer_container_registry_based_on_prefix

logger = logging.getLogger(__name__)

# the string.format necessitates A LOT of curly braces below!
DOCKER_INSPECT_CMD = 'docker inspect {container_id} --format="{{{{{field}}}}}"'
DOCKER_RUNNING_FLAG = 'running' # the "state" when a container is running
DOCKER_EXITED_FLAG = 'exited' # the "state" when a container has exited (for whatever reason)

def get_tag_format(docker_repo_prefix):
    '''
    Returns a format string specific to the Docker repo prefix provided.

    for instance, with github repos (identified by "ghcr.io"), we have tags
    that look like "sha-<hash>".  For Dockerhub, we might only have the hash
    '''
    registry = infer_container_registry_based_on_prefix(docker_repo_prefix)
    return registr.TAG_FORMAT 

def check_image_exists(img_str):
    logger.info('Check if {img} exists.'.format(img = img_str))
    manifest_cmd = 'docker manifest inspect {img}'.format(img = img_str)
    try:
        stdout, stderr = run_shell_command(manifest_cmd)
        logger.info('Successfully found Docker image')
        return True
    except Exception as ex:
        logger.info('Docker image lookup failed.')
        return False

def get_image_name_and_tag(git_repository_name, commit_hash):
    container_registry = get_container_registry()
    org = settings.DOCKER_REPO_ORG
    full_image_url = container_registry.construct_image_url(org, git_repository_name, commit_hash)
    return full_image_url

def pull_image(remote_container_url):
    '''
    Provided with a fully qualifed docker image
    url, pull the image to this machine. 
    '''
    pull_cmd = 'docker pull {x}'.format(x=remote_container_url)
    try:
        stdout, stderr = run_shell_command(pull_cmd)
        logger.info('Successfully pulled Docker image')
    except Exception as ex:
        logger.error('Docker pull failed.')
        raise ex

def get_logs(container_id):
    '''
    Queries the logs from a given container
    '''
    log_cmd = 'docker logs {id}'.format(id=container_id)
    logger.info('Query Docker logs with: {cmd}'.format(cmd=log_cmd))
    try:
        stdout, stderr = run_shell_command(log_cmd)
        logger.info('Successfully queried container logs: {id}.'.format(id=container_id))
        return stdout.decode('utf-8')
    except Exception as ex:
        logger.error('Query of container logs did not succeed.')
        return ''

def remove_container(container_id):
    rm_cmd = 'docker rm {id}'.format(id=container_id)
    logger.info('Remove Docker container with: {cmd}'.format(cmd=rm_cmd))
    stdout, stderr = run_shell_command(rm_cmd)
    logger.info('Successfully removed container: {id}.'.format(id=container_id))

def check_if_container_running(container_id):
    '''
    Queries the status of a docker container to see if it is still running.
    Returns True if running, False if exited.
    '''
    field = '.State.Status'
    cmd = DOCKER_INSPECT_CMD.format(container_id=container_id, field=field)
    logger.info('Inspect Docker container with: {cmd}'.format(cmd=cmd))
    try:
        stdout, stderr = run_shell_command(cmd)
    except Exception as ex:
        logger.error('Caught an exception when checking for running container.'
            ' This can be caused by a race condition if the timestamp on the'
            ' ExecutedOperation is not committed to the database before the second'
            ' request is issued. '
        )
        return False
    stdout = stdout.decode('utf-8').strip()
    if stdout == DOCKER_EXITED_FLAG:
        return False
    elif stdout == DOCKER_RUNNING_FLAG:
        return True
    else:
        logger.info('Received a container status of: {status}'.format(
            status=stdout
        ))
        #TODO inform admins so we can track this case.
        # returning True here (in this potential edge case) makes the container
        # essentially permanant until we resolve its status.
        return True

def check_container_exit_code(container_id):
    '''
    Queries the status of a docker container to see the exit code.
    Note that running containers will give an exit code of zero, so this
    should NOT be used to see if a container is still running.
    '''
    field = '.State.ExitCode'
    cmd = DOCKER_INSPECT_CMD.format(container_id=container_id, field=field)
    logger.info('Inspect Docker container with: {cmd}'.format(cmd=cmd))
    stdout, stderr = run_shell_command(cmd)
    logger.info('Results of inspect:\n\nSTDOUT: {stdout}\n\nSTDERR: {stderr}'.format(
        stdout = stdout,
        stderr = stderr
    ))
    try:
        exit_code = int(stdout)
        return exit_code
    except ValueError as ex:
        logger.error('Received non-integer exit code from container: {id}'.format(
            id=container_id
        ))
        #TODO: do anything else here?

def get_timestamp_as_datetime(container_id, field):
    cmd = DOCKER_INSPECT_CMD.format(container_id=container_id, field=field)
    logger.info('Inspect Docker container with: {cmd}'.format(cmd=cmd))
    stdout, stderr = run_shell_command(cmd)

    # the timestamp by Docker is given like: b'"2020-09-28T17:51:52.393865325Z"\n'
    # so we need to convert to a string (from bytes), and strip off the end-line
    # and other stuff, like excessive microsends...
    try:

        time_str = stdout.decode('utf-8').strip()[:-2].split('.')[0]
        t = datetime.datetime.strptime(time_str, '%Y-%m-%dT%H:%M:%S')
        return t
    except Exception as ex:
        logger.error('Could not parse a timestamp from the Docker inspect command.'
            ' The timestamp string was: {s}. The raw string was: {r}'.format(
                s=time_str,
                r = stdout.decode('utf-8')
            )
        )

def get_finish_datetime(container_id):
    return get_timestamp_as_datetime(container_id, '.State.FinishedAt')

def get_runtime(container_id):
    start_datetime = get_timestamp_as_datetime(container_id, '.State.StartedAt')
    finish_datetime = get_finish_datetime(container_id)
    dt = finish_datetime - start_datetime
    return dt
