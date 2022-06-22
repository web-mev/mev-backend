import logging

from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)

def get_storage_implementation(path):
    '''
    Given a path, examine the file prefix to determine where a 
    resource is stored. Return a "storage backend" class type
    '''

    # a dictionary which maps the filesystem prefix to the 
    # implementation of the storage class (as a "dot string")
    storage_backend_mapping = {
        'gs:': 'api.storage_backends.google_cloud.GoogleBucketStorage'
    }

    prefix = path.split('/')[0]
    try:
        implementing_class_str = storage_backend_mapping[prefix]
    except KeyError as ex:
        logger.info('Could not find an implementation class for'
            ' the file at: {p}.'.format(
                p=path
            ))
        if (len(prefix) > 0) and (prefix[-1] == ':'):
            raise Exception('The path {p} is prefixed by {prefix} and seems to indicate a'
                ' scheme that has not been implemented.'.format(
                    p = path,
                    prefix = prefix
                )
            )
        else:
            logger.info('Since the prefix did not end with a colon, we are assuming it was not'
                ' intended to be a scheme and it is instead a local file in local storage.'
            )
            implementing_class_str = 'api.storage_backends.local.LocalStorage'
    try:
        implementing_class = import_string(implementing_class_str)
    except Exception as ex:
        logger.error('Could not successfully import the class'
            ' identified by string: {s}'.format(
            s = implementing_class_str
        ))
        raise ex

    return implementing_class()

def localize_remote_resource(resource_instance):
    
    path = resource_instance.path

    instance = get_storage_implementation(path)

    # download the file locally and return that path
    return instance.localize_resource(resource_instance)