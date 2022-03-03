import logging

from django.conf import settings

from github_cr import GithubContainerRegistry

logger = logging.getLogger(__name__)

def get_container_registry():
    container_registry_str = settings.CONTAINER_REGISTRY
    logger.info('Get the desired container registry:'
        ' {x}'.format(x=container_registry_str))
    if container_registry_str.lower() == 'github':
        logger.info('Selected the Github container registry')
        return GithubContainerRegistry()
    else:
        err_msg = ('Invalid container registry'
            ' selected: {x}'.format(x = container_registry_str)
        )
        logger.error(err_msg)
        raise Exception(err_msg)