from pathlib import Path
import sys

from django.core.management.base import BaseCommand
from django.conf import settings

from api.models import Operation, PublicDataset
from api.utilities.ingest_operation import perform_operation_ingestion
from api.public_data import get_implementing_class, query_dataset


class Command(BaseCommand):

    help = ('Bring the ephemeral partition up to date with the database and'
            ' warn about required actions')

    def add_arguments(self, parser):
        # argument to control whether we push to github.  Note that it is
        # "paired" with the one below to create a more conventional
        # "switch flag"
        parser.add_argument(
            '-d',
            '--dir',
            default='/data',
            help=('The directory where everything will'
                  ' be populated. Must already exist.')
        )
        parser.add_argument(
            '-f',
            '--force',
            action='store_true',
            help=('A flag which indicates whether we force'
                  ' overwrites of the operation directory.'
                  ' False by default.')
        )

    def handle(self, *args, **options):

        # first check that the required directories are there:
        op_dir = Path(settings.OPERATION_LIBRARY_DIR)
        public_data_dir = Path(settings.PUBLIC_DATA_DIR)
        
        required_dirs = [op_dir, public_data_dir]
        for d in required_dirs:
            if not d.exists():
                sys.stderr.write(f'The expected path {d} did not exist.')
                sys.exit(1)

        # Note that we need to pull ALL the operations, not just
        # the active ones. Display of the executed operations depends
        # on the reference to the Operation instance, even though it
        # has since expired.
        all_operations = Operation.objects.all()

        for op in all_operations:
            git_commit = op.git_commit
            repo_url = op.repository_url
            if repo_url:
                perform_operation_ingestion(repo_url,
                    str(op.pk), git_commit, overwrite=options['force'])
            else:
                sys.stdout.write('\n\n\nWARNING: Operation {op} did not have'
                    ' a repository url. This can be the case for "static"'
                    ' operations that are distributed with WebMeV\n\n\n')


        # We can also have indexed public datasets that were 'active' in a prior
        # deployment. We need to ensure the data is present. We simply report on what's 
        # required rather than assuming the public data is saved in a particular location
        all_datasets = PublicDataset.objects.all()

        for dataset in all_datasets:
            if dataset.active:
                index_name = dataset.index_name
                dataset_cls = get_implementing_class(index_name)
                dataset_dir = Path(dataset_cls.ROOT_DIR)
                if not dataset_dir.exists():
                    sys.stderr.write('The database included a public'
                        f' dataset with index name {index_name}, but no'
                        ' folder for this dataset could be found.')
                    sys.exit(1)
                # now look at the file mapping attribute:
                for key,vals in dataset.file_mapping.items():
                    for val in vals:
                        p = Path(val)
                        if not p.exists():
                            sys.stderr.write('The database included a public'
                                f' dataset expecting a file at {p},'
                                ' but this was not found.')
                            sys.exit(1)      
                # now try a wildcard query to check that the solr index
                # is prepped and ready.
                try:
                    query_dataset(index_name, 'q=*:*&rows=1')
                except Exception as ex:
                    sys.stderr.write(f'Failed on querying {index_name}.'
                        ' Error was {ex}. Check that the solr index exists'
                        ' and has not been corrupted.')
                    sys.exit(1)