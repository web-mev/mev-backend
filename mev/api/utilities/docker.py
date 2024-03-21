import datetime
import logging

from django.conf import settings

from api.utilities.basic_utils import run_shell_command
from api.utilities.admin_utils import alert_admins
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
    return registry.TAG_FORMAT 


def check_image_exists(img_str):
    logger.info('Check if {img} exists.'.format(img = img_str))
    manifest_cmd = 'docker manifest inspect {img}'.format(img = img_str)
    try:
        stdout, stderr = run_shell_command(manifest_cmd)
        logger.info('Successfully found Docker image')
        return True
    except Exception as ex:
        logger.info('Docker image by manifest lookup failed. Attemping a pull')
    
    try:
        pull_image(img_str)
        return True
    except Exception as ex:
        return False


def get_image_name_and_tag(git_repository_name, commit_hash):
    container_registry = get_container_registry()
    org = settings.DOCKER_REPO_ORG
    full_image_url = container_registry.construct_image_url(
        org.lower(), git_repository_name.lower(), commit_hash)
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
        alert_admins(f'Received a Docker exit code'
            ' that was unexpected. Container was: {container_id}')
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


def check_image_name_validity(full_image_name, repo_name, git_hash):
    '''
    This function checks the Docker image name and tag to assert
    that it is valid for a WebMeV Operation, editing it to create
    a final, valid name if necessary. Used when ingesting new tools
    into WebMeV.

    The motivation is that we strive to maintain workflows that are 
    completely reproducible. Part of this includes properly tagged
    Docker images (e.g. latest is ambiguous). Hence, we typically
    associate the tag with something unambiguous such as the git
    commit ID. This function modifies untagged, potentially ambiguous
    images so that this is clear.

    There are a couple situations:
    1. an image is directly related to the repository being ingested 
        (e.g. it is built off an Dockerfile which is part of the tool's repo).
        In this case the image is NOT tagged with the commit hash in the file since
        we don't have that commit hash until AFTER we make the commit. We
        obviously cannot know the tag in advance and provide that tag
        in the workflow file. Thus, we check that the tagged image can be found
        (e.g. in github CR or dockerhub) and then edit the NF file to tag
        it. IF the image does happen to have a tag, then we do NOT edit it.
        It is possible that a new commit may try to use an image built off a 
        previous commit. While that is not generally how we advise, it's not
        incorrect since we have an umambiguous container image reference.
    
    2. An image is from external resources and hence NEEDS a tag. An example
        might be use of a samtools Docker. It would be unnecessary to create our
        own samtools docker. However, we need to unambiguously know which samtools
        container we ended up using.
    '''
    # full_image_name is something like 
    # ghcr.io/web-mev/pca:sha-abcde1234
    # quay.io/biocontainers/samtools
    # docker.io/ubuntu:bionic
    # in the format of <registry>/<org>/<name>:<tag>
    # or <registry>/<name>:<tag>
    # (recall the tag does not need to exist- see below)
    split_full_name = full_image_name.split(':')
    if len(split_full_name) == 2: #if a tag is specified
        image_prefix, tag = split_full_name
        image_is_tagged = True
        logger.info('Docker image was tagged.'
            f'Image name was {image_prefix} with tag {tag}')
    elif len(split_full_name) == 1: # if no tag
        image_prefix = split_full_name[0]
        image_is_tagged = False
        logger.info('Docker image was NOT tagged.'
            f'Image name was {image_prefix}.')
    else:
        logger.error('Could not properly handle the following docker'
            f' image spec: {full_image_name}')
        raise Exception('Could not make sense of the docker'
            f' image handle: {full_image_name}')

    # Look at the image string (the non-tag portion)
    image_split = image_prefix.split('/')
    if len(image_split) == 3:
        # handles situations like ghcr.io/web-mev/pca
        # or quay.io/biocontainers/samtools
        docker_repo, username, image_name = image_split
    elif len(image_split) == 2:
        # handles situations like choosing docker.io/ubuntu:bionic
        # where there is effectively no 'username'
        docker_repo, image_name = image_split
    else:
        err_msg = ('Could not properly handle the following docker'
            f' image spec: {full_image_name}.\nBe sure to include'
            ' the registry prefix and user/org account')
        logger.error(err_msg )
        raise Exception(err_msg)

    # if the image_name matches the repo, then we are NOT expecting 
    # a tag (see the note above regarding the commit hash)
    # However, a tag MAY exist, in which case we will NOT edit that.
    if image_name == repo_name:
        if not image_is_tagged:
            logger.info('Image name matched the repo, but was NOT tagged')
            tag_format = get_tag_format(docker_repo)
            tag = tag_format.format(hash=git_hash)
            final_image_name = full_image_name + ':' + tag
        else:  # image WAS tagged and associated with this repo
            final_image_name = full_image_name
    else:
        # the image is "external" to our repo, in which case it NEEDS a tag
        if not image_is_tagged:
            raise Exception(f'Since the Docker image {full_image_name}'
                ' had a name indicating it is external to the github'
                ' repository, we require a tag. None was found')
        else: # was tagged AND "external"
            final_image_name = full_image_name

    return final_image_name