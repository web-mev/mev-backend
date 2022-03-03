import logging

from .base import BaseContainerRegistry

logger = logging.getLogger(__name__)

class GithubContainerRegistry(BaseContainerRegistry):
    # docker pull ghcr.io/web-mev/pca:sha-458d29d5c1a55d706050af8bd30d92b9621a6f55
    # The 'domain' for the github registry
    PREFIX = 'ghcr.io'

    # The format for an image held in the github container registry. 
    # Note that the format is not fixed, but rather dictated by the process
    # (e.g. github actions) which creates the container. 
    # Here, we expect that the image is tagged with the SHA of the desired commit
    IMAGE_FORMAT = PREFIX + '/{org}/{repo}:sha-{hash}'
