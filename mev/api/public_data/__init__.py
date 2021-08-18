import datetime
import logging

from api.models import PublicDataset
from .sources.gdc.tcga import TCGARnaSeqDataSource
from .indexers import get_indexer


logger = logging.getLogger(__name__)

# This is a set of the available public datasets.
# While the database maintains metadata about the datasets, it has no
# concept of the implementation of said datasets. Thus, we use this list
# as a check. Even if the database reports that a particular dataset is
# available, the lack of a corresponding implementation will stop any further
# actions like querying, etc.
# Add the classes to this list as necessary:
IMPLEMENTING_CLASSES = [
    TCGARnaSeqDataSource
]

DATASET_MAPPING = {x.TAG:x for x in IMPLEMENTING_CLASSES}

# Note that we explicitly create this list (instead of using the keys method
# on DATASET_MAPPING) so that we can check that all names are unique in a unit
# test. If we just used the keys method on the dict, then we wouldn't see that.
DATASETS = [x.TAG for x in IMPLEMENTING_CLASSES]


def check_if_valid_public_dataset_name(dataset_id):
    '''
    A basic method that will return a boolean depending on whether
    the passed string (which represents a dataset/solr collection)
    corresponds to an actual implementing class.
    '''
    return dataset_id in DATASETS

def add_dataset(dataset_db_instance):
    '''
    This is the main entrypoint for all public datasets to be created or updated

    Calls to this function should have already checked that the requested
    dataset name is "valid" using the check_if_valid_public_dataset_name
    function in this module.
    '''

    # Get the class which will do all the work and instantiate it
    implementing_class = DATASET_MAPPING[dataset_db_instance.index_name]
    dataset = implementing_class()

    # If an exception is raised during this call, the calling function (
    # a celery task) will catch and handle it.
    dataset.prepare()

    # Once the data load and index process has successfully completed,
    # update the database model and save:
    dataset_db_instance.public_name = dataset.PUBLIC_NAME
    dataset_db_instance.description = dataset.DESCRIPTION
    dataset_db_instance.timestamp = datetime.datetime.today()
    dataset_db_instance.active = True
    dataset_db_instance.save()

def query_dataset(dataset_id, query_payload):
    '''
    This is the interface for the view functions to query the index
    for data meeting specific filters/criteria

    `dataset_id` is a unique ID string (corresponds to the unique `index_name`
    field of the database table containing public dataset metadata)

    `query_payload` is a dict which contains the query parameters. 

    The indexers should be able to interpret these two args and form
    the proper query, which is dependent on the indexer technology (e.g. solr)
    '''

    # instantiate the indexer we're using
    indexer_cls = get_indexer()
    indexer = indexer_cls()

    if check_if_valid_public_dataset_name(dataset_id):
        return indexer.query(dataset_id, query_payload)
    else: 
        raise Exception('The requested public dataset ({d})'
        ' could not be found.'.format(d=dataset_id))