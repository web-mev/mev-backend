import shutil
import os
import sys

from django.core.management.base import BaseCommand
from api.models import Operation

class Command(BaseCommand):
    help = 'Moves all the files to a user-specific resource directory so the edited database paths work correctly.'

    def add_arguments(self, parser):

        parser.add_argument(
            '-d',
            '--dir',
            help='The path to a folder which has the operations.'
        )

        parser.add_argument(
            '-o',
            '--output_dir',
            help='The path to a folder where the op folders will be moved to.'
        )

    def handle(self, *args, **options):

        all_ops = Operation.objects.all()

        for op in all_ops:
            op_uuid = op.pk
            expected_op_dir = os.path.join(options['dir'], str(op_uuid))
            if os.path.exists(expected_op_dir):
                shutil.move(expected_op_dir, options['output_dir'])
            else:
                sys.stderr.write('Could not locate the expected operation directory at {d}'.format(d=expected_op_dir))
                sys.exit(1)
