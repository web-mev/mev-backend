import os

from django.core.management.base import BaseCommand

from api.models import Operation as OperationDbModel
from api.uploaders import uploader_list
from api.utilities.ingest_operation import ingest_dir

class Command(BaseCommand):
    help = 'Adds operations that are packaged as part of WebMEV'

    def handle(self, *args, **options):
        for uploader_cls in uploader_list:
            op_uuid = uploader_cls.op_id
            op_dir = uploader_cls.op_dir

            if not os.path.exists(op_dir):
                sys.stdout.write('Expected a directory containing'
                    ' operation components at: {d}.'.format(
                        d = op_dir
                    )
                )
                sys.exit(1)
            else:
                ingest_dir(op_dir, op_uuid, '', '', '')