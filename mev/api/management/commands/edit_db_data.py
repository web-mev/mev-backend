import os
import shutil

from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth import get_user_model

from api.models import Resource, ExecutedOperation

class Command(BaseCommand):
    help = ('Edit the database resource table to change paths that reference'
        ' a storage bucket and change them to reference local files. Only used'
        ' for creating a local server.'
        )

    def add_arguments(self, parser):

        # argument to control whether we push to github.  Note that it is
        # "paired" with the one below to create a more conventional "switch flag"
        parser.add_argument(
            '-e',
            '--email',
            help='The email for the user who will own all the resources. Creates on if it does not exist.'
        )

        parser.add_argument(
            '-p',
            '--password',
            help='The password for the user who will own all the resources.'
        )

        parser.add_argument(
            '-d',
            '--dir',
            help='The path to a folder containing user files. This is the exported directory. If you list the directory, you should get a bunch of folders for each user UUID.'
        )

    def handle(self, *args, **options):

        # create an account which will be owned by the superuser
        owner_and_creation_tuple = get_user_model().objects.get_or_create(email=options['email'])
        owner = owner_and_creation_tuple[0]
        owner.set_password(options['password'])

        all_resources = Resource.objects.all()

        # Change all the paths AND owners for the resources
        for r in all_resources:

            original_path = r.path
            # original_path is something like:
            # gs://<bucket>/user_resources/<user UUID>/file.txt
            # and the split creates a list like:
            # ['gs:', '', '<bucket>', 'user_resources', '<user UUID>', 'file.txt']
            # Hence, relative path ends up being: '<user UUID>/file.txt'
            path_contents = original_path.split('/')
            original_user_uuid = path_contents[-2]
            filename = path_contents[-1]

            # this is where the new file will be located, relative to the storage root.
            relative_path = '/'.join([str(owner.pk), filename])

            # The local path on the machine is at /vagrant/mev/user_resources
            # The final part of that path is technically configurable via the 
            # LOCAL_STORAGE_DIRNAME environment variable.
            root_dir = '/vagrant/mev/' + os.environ['LOCAL_STORAGE_DIRNAME']
            final_path = os.path.join(root_dir, relative_path)
            r.path = final_path
            print('%s --> %s' % (original_path, final_path))
            # reset the owner:
            r.owner = owner

            # and save the resource
            r.save()

            # Now move the actual file:
            # TODO: make more robust
            original_localized_filepath = os.path.join(options['dir'], original_user_uuid, filename)
            if not os.path.exists(os.path.dirname(final_path)):
                os.makedirs(os.path.dirname(final_path))
            shutil.move(original_localized_filepath, final_path)
            print('mv %s ---> %s' % (original_localized_filepath, final_path))

        # Now change the ownership of the executed operations
        all_exec_ops = ExecutedOperation.objects.all()
        for x in all_exec_ops:
            x.owner = owner
            x.save()








