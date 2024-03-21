import os
import uuid
import shutil
import sys
import logging

from django.core.management.base import BaseCommand
from django.db.utils import IntegrityError
from django.conf import settings

from api.models import Operation as OperationDbModel
from api.uploaders import uploader_list
from api.utilities.ingest_operation import ingest_dir
from api.utilities.basic_utils import recursive_copy


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
                    db_op = OperationDbModel.objects.create(active=False)
                except IntegrityError as ex:
                    logger.info('Operation was already in database. Skipping db entry,'
                        ' but overwriting the operation contents.'
                    )

                staging_dir = os.path.join(settings.CLONE_STAGING_DIR, str(uuid.uuid4()))
                recursive_copy(op_dir, staging_dir,
                   include_hidden=True)
                try:
                    ingest_dir(staging_dir, str(db_op.pk), git_hash, dir_name, '', overwrite=True)
                except Exception as ex:
                    logger.info('Failed to ingest directory. See logs.'
                                ' Exception was: {ex}'.format(ex=ex)
                                )
                    raise ex
                finally:
                    # remove the staging dir:
                    shutil.rmtree(staging_dir)

                    # inactivate older apps with the same name. This covers situations
                    # where we push an update and the database has an existing/active
                    # Operation.
                    # Query for the updated app-
                    db_op = OperationDbModel.objects.get(pk=db_op.pk)
                    op_name = db_op.name
                    matching_ops = OperationDbModel.objects.filter(name=op_name)
                    for op in matching_ops:
                        if op.pk != db_op.pk:
                            op.active = False
                            op.save()