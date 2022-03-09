class BaseContainerRegistry(object):
    '''
    A base class from which all implementations of a container registry
    should inherit.

    Note that this is NOT an actual registry. Rather, it's an interface
    to registries such as github, dockerhub, etc. 
    '''
    
    def construct_image_url(self, org, src_repo_name, commit_hash):
        raise NotImplementedError('This method needs to be provided in a child class.')