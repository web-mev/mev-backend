import logging

from celery import shared_task

from django.contrib.auth import get_user_model

from api.public_data import create_dataset_from_params

logger = logging.getLogger(__name__)


@shared_task(name='create_dataset_from_params')
def async_create_dataset_from_params(dataset_id, 
        user_pk, 
        request_filters,
        output_name):
    '''
    This function initiates the call to the function responsible
    for creating a dataset given a user's filtering params. By making
    into an async function, we don't tie up the front end for larger
    dataset creation.
    '''
    user = get_user_model().objects.get(pk=user_pk)
    create_dataset_from_params(
        dataset_id, 
        user, 
        request_filters,
        output_name
    )