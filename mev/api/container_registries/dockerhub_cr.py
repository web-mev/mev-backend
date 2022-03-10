import logging

from .base import BaseContainerRegistry

logger = logging.getLogger(__name__)

class DockerhubRegistry(BaseContainerRegistry):
    '''
    Registry class for working with the Dockerhub registry
    '''
    # docker.io/web-mev/pca:sha-458d29d5c1a55d706050af8bd30d92b9621a6f55
    # The 'domain' for the github registry
    PREFIX = 'docker.io'

    # How we expect the image tags to be formatted
    TAG_FORMAT = '{hash}'

    # The format for an image held in the dockerhub container registry. 
    # Here, we expect that the image is tagged with the SHA of the desired commit
    IMAGE_FORMAT = '{org}/{repo}:' + TAG_FORMAT

    def construct_image_str(self, org, src_repo_name, commit_hash):
        '''
        Returns the image "name" for a dockerhub-based container, e.g.
        web-mev/pca:458d29d5c1a55d706050af8bd30d92b9621a6f55
        '''
        return DockerhubRegistry.IMAGE_FORMAT.format(
            org = org,
            repo = src_repo_name,
            hash = commit_hash
        )

    def construct_image_url(self, org, src_repo_name, commit_hash):
        '''
        Returns the full image URL as one might use for a pull operation
        docker.io/web-mev/pca:458d29d5c1a55d706050af8bd30d92b9621a6f55
        '''
        img_str = self.construct_image_str(org, src_repo_name, commit_hash)

        return '{prefix}/{img}'.format(
            prefix = DockerhubRegistry.PREFIX,
            img = img_str
        )
