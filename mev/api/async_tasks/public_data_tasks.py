import logging

from celery.decorators import task

from api.models import PublicDataset

from api.public_data import add_dataset

logger = logging.getLogger(__name__)

@task(name='prepare_public_dataset')
def prepare_dataset(db_model_pk):
    '''
    This starts the async process of creating or
    updating a public dataset. 

    The arg is the primary key for the PublicDataset
    database model instance
    '''
    try:
        dataset_db_model = PublicDataset.objects.get(pk=db_model_pk)
    except PublicDataset.DoesNotExist:
        logger.error('Could not find the instance of the'
            ' public dataset with pk={pk}. Generally, this should'
            ' not happen.'.format(pk=db_model_pk))
        return 

    try:
        add_dataset(dataset_db_model)
    except Exception as ex:
        logger.info('Caught an exception when preparing a public dataset.'
            ' Exception text was: {x}'.format(x = ex)
        )
         