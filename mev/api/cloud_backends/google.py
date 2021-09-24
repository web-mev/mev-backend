import logging
import os

from django.core.exceptions import ImproperlyConfigured
from django.conf import settings

from api.utilities.basic_utils import get_with_retry


logger = logging.getLogger(__name__)

try:
    GOOGLE_BUCKET_NAME = os.environ['STORAGE_BUCKET_NAME']
except KeyError as ex:
    raise ImproperlyConfigured('Need to supply the following environment'
        ' variable: {k}'.format(k=ex))

def get_instance_region():
    try:
        response = get_with_retry(
            'http://metadata/computeMetadata/v1/instance/zone', 
            headers={'Metadata-Flavor': 'Google'}
        )
        # zone_str is something like 'projects/{project ID number}/zones/us-east4-c'
        zone_str = response.text
        region = '-'.join(zone_str.split('/')[-1].split('-')[:2]) # now like us-east4
        return region
    except Exception as ex:
        # if we could not get the region of the instance, return None for the region
        #return None
        raise ex

def check():
    logger.info('Checking that everything is set for running MEV'
        ' in the Google Cloud environment.'
    )

    # get the location of our application
    #region = get_instance_region()

    if settings.ENABLE_REMOTE_JOBS:
        logger.info('Remote jobs were enabled. Check that the runners are ready.')
    else:
        logger.info('Remote jobs disabled.')

    # check that the bucket region and the VM region are the same.