import os
import logging

from django.core.management.base import BaseCommand

from api.models import PublicDataset
from api.public_data import check_if_valid_public_dataset_name, \
    prepare_dataset

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

    def handle(self, *args, **options):

        dataset_id = options['dataset_id']
        is_valid = check_if_valid_public_dataset_name(dataset_id)

        if is_valid:
            prepare_dataset(dataset_id)
        else:
            logger.info('The requested datase was not valid. Check that you have'
                ' typed the name correctly.'
            )

