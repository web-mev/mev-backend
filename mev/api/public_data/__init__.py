import datetime
import os
import logging

from api.models import PublicDataset, Resource
from api.utilities.resource_utilities import move_resource_to_final_location, \
    get_resource_size
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

def get_implementing_class(index_name):
    implementing_class = DATASET_MAPPING[index_name]
    return implementing_class()

def prepare_dataset(dataset_id):
    '''
    This is the main entrypoint for all public datasets to be created or updated

    Calls to this function should have already checked that the requested
    dataset name is "valid" using the check_if_valid_public_dataset_name
    function in this module.

    Note that this only downloads and prepares the dataset. Does NOT index!
    '''

    # Get the class which will do all the work and instantiate it
    dataset = get_implementing_class(dataset_id)
    dataset.prepare()

def index_dataset(dataset_db_instance, file_mapping):
    '''
    Indexes a subset of the files provided as a dict in the second arg.
    Specifics of the indexing are left to the implementing class and
    may affect which changes are committed.

    `file_mapping` is a dict of keys pointing at file paths. Some of these
    files are indexed, while others are just there to verify the integrity
    of the entire dataset.

    for instance, in the TCGA RNA-seq data, we ONLY index the annotation/metadata
    file, but we still require the presence of a count matrix. 
    '''

    # temporarily inactivate the dataset:
    dataset_db_instance.active = False
    dataset_db_instance.save()

    # the unique dataset ID
    index_name = dataset_db_instance.index_name

    # the implementing class for this dataset
    dataset = get_implementing_class(index_name)

    dataset.verify_files(file_mapping)

    files_to_index = dataset.get_indexable_files(file_mapping)

    # get the implementation for the indexing tool and instantiate
    indexer = get_indexer()
    for filepath in files_to_index:
        try:
            indexer.index(index_name, filepath)
        except Exception as ex:
            return

    # Once the index process has successfully completed,
    # update the database model and save:
    dataset_db_instance.public_name = dataset.PUBLIC_NAME
    dataset_db_instance.description = dataset.DESCRIPTION
    dataset_db_instance.timestamp = datetime.datetime.today()
    dataset_db_instance.active = True
    dataset_db_instance.file_mapping = file_mapping
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
    indexer = get_indexer()

    if check_if_valid_public_dataset_name(dataset_id):
        return indexer.query(dataset_id, query_payload)
    else: 
        raise Exception('The requested public dataset ({d})'
        ' could not be found.'.format(d=dataset_id))

def create_dataset_from_params(dataset_id, user, request_payload):
    '''
    This will create a Resource based on the request
    payload. Note that if request_payload is None, then we 
    do not apply any filtering 
    '''

    if not check_if_valid_public_dataset_name(dataset_id):
        raise Exception('Dataset identifier was not valid.')

    ds = get_implementing_class(dataset_id)
    dataset_db_instance = PublicDataset.objects.get(index_name = dataset_id)
    if not dataset_db_instance.active:
        #TODO: improve message
        raise Exception('The requested dataset was not active. If this'
            ' does not resolve, please contact an administrator.'
        )
    try:
        path_list, resource_type_list = ds.create_from_query(
            dataset_db_instance,
            request_payload
        )
    except Exception as ex:
        logger.info('An error occurred when preparing the file based'
             ' on the following query params: {d}.'.format(d=request_payload)
        )
        raise ex

    # create the Resource instances.
    resource_list = []
    for path, resource_type in zip(path_list, resource_type_list):
        r = Resource.objects.create(
            owner = user,
            path = path,
            resource_type = resource_type
        )

        # move to the final location and modify some attibutes.
        # Note that we don't use the `validate_and_store_resource` function
        # in the resource_utilities module as we have full control over the 
        # creation of the file above. If we create an invalid file, then we 
        # have other problems.
        r.path = move_resource_to_final_location(r)
        r.is_active = True
        r.size = get_resource_size(r)
        r.save()

        resource_list.append(r)

    return resource_list