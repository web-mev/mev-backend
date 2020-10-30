import logging
import os

from django.core.exceptions import ImproperlyConfigured
from django.conf import settings

from api.utilities.basic_utils import get_with_retry
from api.runners import get_runner
from api.storage_backends.google_cloud import GoogleBucketStorage

logger = logging.getLogger(__name__)

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

def startup_check():
    logger.info('Checking that everything is set for running MEV'
        ' in the Google Cloud environment.'
    )

    # get the location of our application
    region = get_instance_region()

    if settings.ENABLE_REMOTE_JOBS:
        logger.info('Remote jobs were enabled. Check that the runners are ready.')
        for job_runner in settings.REQUESTED_REMOTE_JOB_RUNNERS:
            runner_class = get_runner(name=job_runner)
            runner = runner_class()
            try:
                runner.check_if_ready()
            except ImproperlyConfigured as ex:
                logger.info('Runner was not ready.')
                raise ex
            except Exception as ex:
                logger.info('Unexpected error upon checking if runners were ready.')
                raise ex
    else:
        logger.info('Remote jobs disabled.')

    # check that the bucket region and the VM region are the same.
    # we could technically permit them to be different, but this can cause 
    # issues pushing data between regions.
    if not settings.STORAGE_LOCATION == settings.LOCAL:
        logger.info('Since storage is not local, have to check regions.')
        gbs = GoogleBucketStorage()
        bucket_location = gbs.get_bucket_region(gbs.BUCKET_NAME)
        if bucket_location != region:
            raise ImproperlyConfigured('The storage bucket ({b})'
                ' should be in the same region ({r}) as the host machine.'.format(
                    b = gbs.BUCKET_NAME,
                    r = region
                )
            )
        else:
            logger.info('Bucket region matched the instance region.')


