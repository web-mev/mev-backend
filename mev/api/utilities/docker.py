import subprocess as sp
import logging

from django.conf import settings

logger = logging.getLogger(__name__)

def build_docker_image(image, tag, dockerfile, context_dir):
    '''
    Prepares the Operation, including building and pushing the Docker container

    `operation_dir` is the directory where the staged repository is held
    `git_hash` is the commit hash and it allows us to version the docker container
        the same as the git repository
    '''

    DOCKER_BUILD_CMD = 'docker build -t {username}/{image}:{tag} -f {dockerfile} {context_dir}'

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
    build_cmd = build_cmd.split(' ')

    p = sp.Popen(build_cmd, stdout=sp.PIPE, stderr=sp.STDOUT)
    stdout, stderr = p.communicate()
    if p.returncode != 0:
        logger.error('Problem with building the'
            ' Docker image at {context_dir}.\n'
            'STDERR was: {stderr}\nSTDOUT was: {stdout}'.format(
                context_dir=context_dir,
                stderr=stderr,
                stdout=stdout
            )
        )
        raise Exception('Failed when building the Docker image. See logs.')
    else:
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
    login_cmd = login_cmd.split(' ')

    p = sp.Popen(login_cmd, stdout=sp.PIPE, stderr=sp.STDOUT)
    stdout, stderr = p.communicate()
    if p.returncode != 0:
        logger.error('Problem with logging into'
            ' Dockerhub.\n'
            'STDERR was: {stderr}\nSTDOUT was: {stdout}'.format(
                stderr=stderr,
                stdout=stdout
            )
        )
        raise Exception('Failed when logging into Dockerhub. See logs.')
    else:
        logger.info('Successfully logged into Dockerhub')   

def push_image_to_dockerhub(image, tag):

    DOCKER_PUSH_CMD = 'docker push {username}/{image}:{tag}'
    push_cmd = DOCKER_PUSH_CMD.format(
        username = settings.DOCKERHUB_USERNAME,
        image = image,
        tag = tag
    ) 
    logger.info('Push Docker image with: {cmd}'.format(cmd=push_cmd))
    push_cmd = push_cmd.split(' ')

    p = sp.Popen(push_cmd, stdout=sp.PIPE, stderr=sp.STDOUT)
    stdout, stderr = p.communicate()
    if p.returncode != 0:
        logger.error('Problem with pushing the'
            ' Docker image {image}/{tag}.\n'
            'STDERR was: {stderr}\nSTDOUT was: {stdout}'.format(
                image=image,
                tag = tag,
                stderr=stderr,
                stdout=stdout
            )
        )
        raise Exception('Failed when pushing the Docker image. See logs.')
    else:
        logger.info('Successfully pushed image.')