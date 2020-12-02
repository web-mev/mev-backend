import os

from django.core.management.base import BaseCommand

from api.models import Operation as OperationDbModel
from api.uploaders import uploader_list
from api.utilities.ingest_operation import ingest_dir
from api.utilities.basic_utils import dir_hash

class Command(BaseCommand):
    help = 'Adds operations that are packaged as part of WebMEV'

    def handle(self, *args, **options):
        for uploader_cls in uploader_list:
            op_uuid = uploader_cls.op_id
            op_dir = uploader_cls.op_dir

            if (not os.path.exists(op_dir)) or (not os.path.isdir(op_dir)):
                sys.stdout.write('Expected a directory containing'
                    ' operation components at: {d}.'.format(
                        d = op_dir
                    )
                )
                sys.exit(1)
            else:
                # in lieu of a github-provided hash, we use the 
                # function below which calculates a hash of the directory
                # containing the operation's files
                hash_of_dir = dir_hash(op_dir)

                # For operations that are run on the local docker engine,
                # for instance, we name the docker image based on the github
                # repository. Lacking that, we give the name as the name
                # of the directory containing the operation's files.
                if op_dir.endswith('/'):
                    dir_name = os.path.basename(os.path.dirname(op_dir))
                else:
                    dir_name = os.path.basename(op_dir)
                                
                # create the database object-- the ingestion assumes a non-active
                # Operation was created prior to ingestion
                db_op = OperationDbModel.objects.create(id=op_uuid, active=False)
                ingest_dir(op_dir, op_uuid, hash_of_dir, dir_name, '')