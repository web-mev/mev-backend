import logging
import os

from api.utilities.basic_utils import get_with_retry

logger = logging.getLogger(__name__)

def get_instance_region():
    logger.info('Requesting instance region in GCP...')
    try:
        zone = get_instance_zone() # a string like us-east4-c
        region = '-'.join(zone.split('-')[:2]) # now like us-east4
        return region
    except Exception as ex:
        # if we could not get the region of the instance, return None for the region
        #return None
        raise ex

def get_instance_zone():
    logger.info('Requesting instance zone in GCP...')
    try:
        response = get_with_retry(
            'http://metadata/computeMetadata/v1/instance/zone', 
            headers={'Metadata-Flavor': 'Google'}
        )
        # zone_str is something like 'projects/{project ID number}/zones/us-east4-c'
        zone_str = response.text
        zone = zone_str.split('/')[-1] # now like us-east4-c
        return zone
    except Exception as ex:
        # if we could not get the region of the instance, return None for the region
        #return None
        raise ex