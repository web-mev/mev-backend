from django.conf import settings

class CloudPlatformNotFoundException(Exception):
    pass

def perform_startup_checks():
    '''
    To reduce runtime errors, we need to check that certain
    platform-specific items are ready to go.

    For instance, we want to ensure that the storage bucket and host machine
    are in the same region. 
    '''

    if settings.CLOUD_PLATFORM == settings.GOOGLE:
        import api.cloud_backends.google_cloud as google_cloud
        google_cloud.startup_check()
        return
    raise CloudPlatformNotFoundException()

def get_instance_region():
    '''
    Returns the "region" (as a string) of a compute instance. In the case of GCP, this
    can be something like "us-east4"
    '''
    if settings.CLOUD_PLATFORM == settings.GOOGLE:
        import api.cloud_backends.google_cloud as google_cloud
        return google_cloud.get_instance_region()

    raise CloudPlatformNotFoundException()

def get_instance_zone():
    '''
    Returns the "zone" (as a string) of a compute instance. In the case of GCP, this
    can be something like "us-east4-c"
    '''
    if settings.CLOUD_PLATFORM == settings.GOOGLE:
        import api.cloud_backends.google_cloud as google_cloud
        return google_cloud.get_instance_zone()

    raise CloudPlatformNotFoundException()