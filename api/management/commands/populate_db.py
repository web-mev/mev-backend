from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from api.models import Workspace, Resource
from api.tests import test_settings

# a global dictionary so that we do not have to pass around the 
# User instances
user_dict = {}

# For consistent reference:
USER1 = 'regular_user1'
USER2 = 'regular_user2'
ADMIN_USER = 'admin_user'

class Command(BaseCommand):
    help = 'Populate the database with some basic data.'

    def populate_users(self):
        user_model = get_user_model()

        # create the regular users in the database
        u1 = user_model.objects.create_user(test_settings.REGULAR_USER_1.email, 
            test_settings.REGULAR_USER_1.plain_txt_password)
        u2 = user_model.objects.create_user(test_settings.REGULAR_USER_2.email, 
            test_settings.REGULAR_USER_2.plain_txt_password)

        # create an admin user in the database
        u3 = user_model.objects.create_user(test_settings.ADMIN_USER.email, 
            test_settings.ADMIN_USER.plain_txt_password)
        u3.is_admin = True
        u3.is_staff = True
        u3.save()

        user_dict[USER1] = u1
        user_dict[USER2] = u2
        user_dict[ADMIN_USER] = u3

    def populate_workspaces(self):
        Workspace.objects.create(owner=user_dict[USER1])
        Workspace.objects.create(owner=user_dict[USER1])
        Workspace.objects.create(owner=user_dict[USER2])

    def populate_resources(self):
        Resource.objects.create(
            owner=user_dict[USER1],
            name='fileA.tsv',
            resource_type = 'Integer table',
            path='/path/to/fileA.txt',
            is_active = True
        )
        Resource.objects.create(
            owner=user_dict[USER1],
            name='fileB.csv',
            resource_type = 'Annotation table',
            path='/path/to/fileB.txt'
        )   
        Resource.objects.create(
            owner=user_dict[USER1],
            name='public_file.csv',
            resource_type = 'Integer table',
            path='/path/to/public_file.txt',
            is_public = True
        )        
        Resource.objects.create(
            owner=user_dict[USER2],
            name='fileC.tsv',
            resource_type = 'Numeric table',
            path='/path/to/fileC.txt'
        )

    def add_resources_to_workspace(self):
        # for regular user1, associate some Resources
        # with a Workspace
        user1_workspaces = Workspace.objects.filter(owner=user_dict[USER1])
        workspace = user1_workspaces[0]

        # create a couple new Resources associated with the first Workspace:
        Resource.objects.create(
            owner=user_dict[USER1],
            name='file1_in_workspace.tsv',
            resource_type = 'Integer table',
            workspace=workspace,
            path='/path/to/file1_in_workspace.tsv'
        )
        Resource.objects.create(
            owner=user_dict[USER1],
            name='file2_in_workspace.tsv',
            resource_type = 'Integer table',
            workspace=workspace,
            path='/path/to/file2_in_workspace.tsv'
        )

    def handle(self, *args, **options):
        self.populate_users()
        self.populate_workspaces()
        self.populate_resources()
        self.add_resources_to_workspace()