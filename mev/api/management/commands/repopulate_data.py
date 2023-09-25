from pathlib import Path
import sys

import boto3
from django.core.management import call_command
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
            default=settings.DATA_DIR,
            help=('The directory where everything will'
                  ' be populated. Must already exist.')
        )
        parser.add_argument(
            '-b',
            '--bucket',
            default=settings.PUBLIC_DATA_BUCKET_NAME,
            help=('The name of the bucket which holds the public'
                  ' data for use by our indexers.')
        )
        parser.add_argument(
            '-f',
            '--force',
            action='store_true',
            help=('A flag which indicates whether we force'
                  ' overwrites of the operation directory.'
                  ' False by default.')
        )

    def attempt_download(self, dest_path, public_data_dir, source_bucket_name):
        """
        Attempt to pull data from the bucket to our local disk. This
        ensures that the api.models.PublicDataset has the expected files.

        Note that the structure of the bucket should match that of our
        public data folder. For instance, if we expect a file at:
        /data/public_data/tcga/foo.hd5

        then the bucket-based object should be at
        s3://<source_bucket_name>/tcga/foo.hd5
        """
        obj_path = dest_path.relative_to(public_data_dir)
        s3 = boto3.client('s3')
        s3.download_file(source_bucket_name, str(obj_path), str(dest_path))

    def attempt_dataset_index(self, public_dataset):
        """
        Use the 'index_data' management command to index the required files.

        Called when the solr index is ready but does not contain any data/rows.
        """
        file_strings = []
        for key, vals in public_dataset.file_mapping.items():
            # note that each key addresses a list of files so we
            # need to iterate:
            for v in vals:
                file_strings.append(f'{key}={v}')
        call_command('index_data', f'--dataset_id={public_dataset.index_name}',
                     *file_strings)

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
                print(f'\n\n\nWARNING: Operation {op.pk} did not have'
                    ' a repository url. This can be the case for "static"'
                    ' operations that are distributed with WebMeV\n\n\n')


        # We can also have indexed public datasets that were 'active' in a prior
        # deployment. We need to ensure the data is present. We simply report on what's 
        # required rather than assuming the public data is saved in a particular location
        all_datasets = PublicDataset.objects.filter(active=True)

        # don't want to bury the warning messages-- save them up 
        # and display at the end of the loop
        warning_messages = []
        for dataset in all_datasets:
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
                        print('The database included a public'
                            f' dataset expecting a file at {p},'
                            ' but this was not found. Try to download.')
                        try:
                            self.attempt_download(p, public_data_dir, options['bucket'])
                        except:
                            sys.stderr.write(f'Failed to download file to {p}. Exiting.')
                            sys.exit(1) 

            # now try a wildcard query to check that the solr index
            # is prepped and ready.
            try:
                r = query_dataset(index_name, 'q=*:*&rows=1')
                if len(r['response']['docs']) == 0:
                    # we have a successful query with zero rows returned if the index
                    # is ready but has not ingested any data. Attempt that here:
                    try:
                        self.attempt_dataset_index(dataset)
                    except Exception as ex:
                        warning_messages.append(f'The index "{index_name}" is'
                                        ' ready, but the indexing process failed.'
                                        f' The reported exception was: {ex}') 
            except Exception as ex:
                sys.stderr.write(f'Failed on querying {index_name}.'
                    f' Error was {ex}. Check that the solr index exists'
                    ' and has not been corrupted.')
                sys.exit(1)

        if len(warning_messages) > 0L
            print('\n\n' + '*'*100 + '\n' + 'WARNINGS:\n')
            print('\n'.join(warning_messages))