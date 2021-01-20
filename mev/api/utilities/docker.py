import datetime
import logging

from django.conf import settings

from api.utilities.basic_utils import run_shell_command

logger = logging.getLogger(__name__)

# the string.format necessitates A LOT of curly braces below!
DOCKER_INSPECT_CMD = 'docker inspect {container_id} --format="{{{{{field}}}}}"'
DOCKER_RUNNING_FLAG = 'running' # the "state" when a container is running
DOCKER_EXITED_FLAG = 'exited' # the "state" when a container has exited (for whatever reason)

def build_docker_image(image, tag, dockerfile, context_dir):
    '''
    Prepares the Operation, including building and pushing the Docker container

    `operation_dir` is the directory where the staged repository is held
    `git_hash` is the commit hash and it allows us to version the docker container
        the same as the git repository
    '''

    DOCKER_BUILD_CMD = 'docker build --no-cache -t {username}/{image}:{tag} -f {dockerfile} {context_dir}'
    
    if len(tag) == 0:
        tag = 'latest'
    
    build_cmd = DOCKER_BUILD_CMD.format(
        username = settings.DOCKERHUB_USERNAME,
        image = image,
        tag = tag,
        dockerfile = dockerfile,
        context_dir = context_dir
    )
    logger.info('Building Docker image for local operation with: {cmd}'.format(
        cmd = build_cmd
    ))
    stdout, stderr = run_shell_command(build_cmd)
    logger.info('Successfully built image.')

def login_to_dockerhub():
    DOCKER_LOGIN_CMD = 'docker login -u {username} -p {password}'

    login_cmd = DOCKER_LOGIN_CMD.format(
        username = settings.DOCKERHUB_USERNAME,
        password = settings.DOCKERHUB_PASSWORD
    )
    logger.info('Attempting login to Dockerhub with: {cmd}'.format(
        cmd = login_cmd
    ))
    stdout, stderr = run_shell_command(login_cmd)
    logger.info('Successfully logged into Dockerhub')   

def push_image_to_dockerhub(image, tag):

    IMAGE_STR = '{username}/{image}:{tag}'
    DOCKER_PUSH_CMD = 'docker push {img_str}'
    image_str = IMAGE_STR.format(
        username = settings.DOCKERHUB_USERNAME,
        image = image,
        tag = tag
    )
    push_cmd = DOCKER_PUSH_CMD.format(
        img_str = image_str
    ) 
    logger.info('Push Docker image with: {cmd}'.format(cmd=push_cmd))
    stdout, stderr = run_shell_command(push_cmd)
    logger.info('Successfully pushed image.')
    return image_str

def get_logs(container_id):
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
    try:
        exit_code = int(stdout)
        return exit_code
    except ValueError as ex:
        logger.error('Received non-integer exit code from container: {id}'.format(
            id=container_id
        ))
        #TODO: do anything else here?

def check_container_logs(container_id):
    '''
    Gets the logs from a container-- processes should dump errors to stderr, but
    this gets anything printed to stdout/stderr
    '''
    cmd = 'docker logs {container_id}'.format(container_id=container_id)
    logger.info('Check logs on local Docker container with: {cmd}'.format(
        cmd = cmd
    ))
    stdout, stderr = run_shell_command(cmd)
    return stdout.decode('utf-8')

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