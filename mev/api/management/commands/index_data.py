import os
import sys
import logging
from collections import defaultdict

from django.core.management.base import BaseCommand

from api.models import PublicDataset
from api.public_data import check_if_valid_public_dataset_name, \
    index_dataset

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = ('Downloads and prepares a specific public dataset.'
    ' Does not create indexes or anything further')

    def add_arguments(self, parser):

        # argument to control whether we push to github.  Note that it is
        # "paired" with the one below to create a more conventional "switch flag"
        parser.add_argument(
            '-d',
            '--dataset_id',
            required=True,
            help='The unique identifier of the public dataset to prepare.'
        )

        parser.add_argument(
            'files',
            metavar='path',
            nargs='+',
            help=('One or more key-value pairs, written as "<key>=<value>" which'
                ' specify which files are germane to this dataset. Is specific to'
                ' each dataset, and it will warn/error accordingly if anything'
                ' is amiss.'
            )
        )

    def validate_kv_pairs(self, files_kv_pairs):
        d = defaultdict(list)
        for s in files_kv_pairs:
            # s should be a string like "a=b"
            # where a is a 'key' and 'b' is the path
            # to a corresponding file
            try:
                k,v = [x.strip() for x in s.split('=')]
                d[k].append(v)
            except ValueError:
                raise Exception('Could not parse the argument "%s" as a key-value pair'
                    ' delimited by "="' % s
                )
        return d

    def handle(self, *args, **options):

        dataset_id = options['dataset_id']
        files_kv_pairs = options['files']
        is_valid = check_if_valid_public_dataset_name(dataset_id)
        file_mapping = self.validate_kv_pairs(files_kv_pairs)

        if is_valid:

            # get or create a model in the database. If the record already exists in the 
            # database, we don't change anything. This will keep the dataset active while
            # things are updated in the background. Of course, once we initiate the index
            # process, we will have to temporarily "hide" the dataset by setting it to be
            # inactive. 
            try:
                dataset_db_model = PublicDataset.objects.get(
                    index_name = dataset_id
                )
                logger.info('Model for dataset {id} existed. '.format(id=dataset_id))
                if dataset_db_model.active:
                    logger.info('The dataset is active, so this process will update it.'
                        ' Note, however, that we will inactivate it during the update.'
                    )
                else:
                    logger.info('The dataset was not active. Once it is correctly indexed, it'
                        ' will be activated.'
                    )

            except PublicDataset.DoesNotExist:
                # By default, the instance is set to inactive. once the data prep is done and indexed, the 
                # active field will be updated.
                logger.info('Creating a public new dataset. This will not be active'
                    ' until it is indexed.'
                )
                dataset_db_model = PublicDataset.objects.create(index_name = dataset_id)
            
            index_dataset(dataset_db_model, file_mapping)
        else:
            logger.info('The requested datase was not valid. Check that you have'
                ' typed the name correctly.'
            )

