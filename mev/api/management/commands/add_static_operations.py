import os
import logging

from django.core.management.base import BaseCommand
from django.db.utils import IntegrityError

from api.models import Operation as OperationDbModel
from api.uploaders import uploader_list
from api.utilities.ingest_operation import ingest_dir

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Adds operations that are packaged as part of WebMEV'

    def add_arguments(self, parser):

        # argument provides the git commit for the current deployment. Used to tag
        # the static operations that are packaged with WebMeV
        parser.add_argument(
            '-c',
            '--commit_id',
            required=True,
            help='The git commit hash'
        )

    def handle(self, *args, **options):

        git_hash = options['commit_id']

        for uploader_cls in uploader_list:
            op_uuid = uploader_cls.op_id
            op_dir = uploader_cls.op_dir

            if (not os.path.exists(op_dir)) or (not os.path.isdir(op_dir)):
                logger.error('Expected a directory containing'
                    ' operation components at: {d}.'.format(
                        d = op_dir
                    )
                )
                sys.exit(1)
            else:

                if op_dir.endswith('/'):
                    dir_name = os.path.basename(os.path.dirname(op_dir))
                else:
                    dir_name = os.path.basename(op_dir)
                                
                # create the database object-- the ingestion assumes a non-active
                # Operation was created prior to ingestion
                try:
                    db_op = OperationDbModel.objects.create(id=op_uuid, active=False)
                except IntegrityError as ex:
                    logger.info('Operation was already in database. Skipping db entry,'
                        ' but overwriting the operation contents.'
                    )

                ingest_dir(op_dir, op_uuid, git_hash, dir_name, '', overwrite=True)