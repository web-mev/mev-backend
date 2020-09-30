import logging

from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)

def localize_remote_resource(resource_instance):
    
    # a dictionary which maps the filesystem prefix to the 
    # implementation of the storage class (as a "dot string")
    storage_backend_mapping = {
        'gs:': 'api.storage_backends.google_cloud.GoogleBucketStorage'
    }

    prefix = resource_instance.path.split('/')[0]
    try:
        implementing_class_str = storage_backend_mapping[prefix]
    except KeyError as ex:
        logger.error('Could not find an implementation class for localizing'
            ' the file at: {p}.'.format(
                p=resource_instance.path
            ))
        raise ex
    try:
        implementing_class = import_string(implementing_class_str)
    except Exception as ex:
        logger.error('Could not successfully import the class'
            ' identified by string: {s}'.format(
            s = implementing_class_str
        ))
        raise ex

    instance = implementing_class()

    # download the file locally and 
    local_path = instance.get_local_resource_path(resource_instance)
    return local_path