from .local import LocalStorage
from .google_cloud import GoogleBucketStorage

from django.core.exceptions import ImproperlyConfigured
from django.conf import settings

def get_storage_backend():
    '''
    Return the class implementing the storage backend appropriate 
    for our environment. If local, does not matter.

    For each cloud environment, we only allow certain storage backends. For example,
    if we are on GCP, we don't allow AWS S3 storage backend (for simplicity)
    '''
    if settings.STORAGE_LOCATION == settings.LOCAL:
        return LocalStorage()
    else: # remote
        if settings.CLOUD_PLATFORM == settings.GOOGLE:
            return GoogleBucketStorage()
        else:
            raise ImproperlyConfigured('Could not find the storage backend.')

