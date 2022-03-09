import logging

from django.conf import settings

from github_cr import GithubContainerRegistry
from dockerhub_cr import DockerhubRegistry

logger = logging.getLogger(__name__)

REGISTRIES = [GithubContainerRegistry, DockerhubRegistry]
REGISTRY_PREFIX_MAP = {
    clazz.PREFIX: clazz for clazz in REGISTRIES
}

def get_container_registry():
    container_registry_str = settings.CONTAINER_REGISTRY
    logger.info('Get the desired container registry:'
        ' {x}'.format(x=container_registry_str))
    if container_registry_str.lower() == 'github':
        logger.info('Selected the Github container registry')
        return GithubContainerRegistry()
    elif container_registry_str.lower() == 'dockerhub':
        logger.info('Selected the Dockerhub container registry')
        return DockerhubRegistry()
    else:
        err_msg = ('Invalid container registry'
            ' selected: {x}'.format(x = container_registry_str)
        )
        logger.error(err_msg)
        raise Exception(err_msg)

def infer_container_registry_based_on_prefix(prefix):
    try:
        # return an instance of the class. The prefix map has the class object, NOT an instance
        return REGISTRY_PREFIX_MAP[prefix]()
    except KeyError as ex:
        raise Exception('The prefix {p} did not correspond to any'
            ' docker registry we are aware of.'
        )