import random 
import os
import uuid
import errno

from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand
from django.conf import settings

from api.models import Workspace, Resource, ResourceMetadata
from api.models import Operation as OperationDbModel
from api.utilities.operations import read_operation_json, \
    validate_operation
from api.serializers.operation import OperationSerializer
from api.utilities.ingest_operation import save_operation
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

        # for creating random file sizes:
        size_low = 1000
        size_high = 1000000000

        Resource.objects.create(
            owner=user_dict[USER1],
            name='fileA.tsv',
            resource_type = 'MTX',
            path='/path/to/fileA.txt',
            is_active = True,
            is_public = True,
            size = random.randint(size_low, size_high)
        )
        Resource.objects.create(
            owner=user_dict[USER1],
            name='fileB.csv',
            resource_type = 'ANN',
            path='/path/to/fileB.txt',
            size = random.randint(size_low, size_high)
        )   
        Resource.objects.create(
            owner=user_dict[USER1],
            name='public_file.csv',
            resource_type = 'I_MTX',
            path='/path/to/public_file.txt',
            is_public = True,
            size = random.randint(size_low, size_high)
        )
        Resource.objects.create(
            owner=user_dict[USER1],
            name='abc.csv',
            resource_type = None,
            path='/path/to/abc.csv',
            is_active = True,
            size = random.randint(size_low, size_high)
        )  
        Resource.objects.create(
            owner=user_dict[USER2],
            name='fileC.tsv',
            resource_type = 'MTX',
            path='/path/to/fileC.txt',
            size = random.randint(size_low, size_high)
        )

        # create a Resource that has the type unset:
        Resource.objects.create(
            owner=user_dict[USER2],
            name='fileD.tsv',
            path='/path/to/fileD.txt',
            size = random.randint(size_low, size_high)      
        )

        # create a Resource that has the same path as another
        # Resource.  This is for testing Resource deletions.
        Resource.objects.create(
            owner=user_dict[USER1],
            name='fileA.tsv',
            resource_type = 'MTX',
            path='/path/to/fileA.txt',
            is_active = True,
            is_public = True,
            size = random.randint(size_low, size_high)
        )

    def add_resources_to_workspace(self):
        # for regular user1, associate some Resources
        # with a Workspace
        user1_workspaces = Workspace.objects.filter(owner=user_dict[USER1])
        if len(user1_workspaces) > 2:
            raise ImproperlyConfigured('Create at least two Workspaces for user: {user}'.format(
                user = user_dict[USER1]))

        workspace = user1_workspaces[0]

        # create a couple new Resources associated with the first Workspace:
        r1 = Resource.objects.create(
            owner=user_dict[USER1],
            name='file1_in_workspace.tsv',
            resource_type = 'I_MTX',
            path='/path/to/file1_in_workspace.tsv',
            is_active = True
        )
        r2 = Resource.objects.create(
            owner=user_dict[USER1],
            name='file2_in_workspace.tsv',
            resource_type = 'I_MTX',
            path='/path/to/file2_in_workspace.tsv',
            is_active = True
        )
        r1.workspaces.add(workspace)
        r2.workspaces.add(workspace)

        # for increased complexity, add r1 to a second workspace
        other_workspace = user1_workspaces[1]
        r1.workspaces.add(other_workspace)

    def add_metadata_to_resources(self):
        all_resources = Resource.objects.all()
        for r in all_resources:
            if r.resource_type is not None:
                rm = ResourceMetadata.objects.create(
                    resource=r,
                    parent_operation=None,
                    observation_set = None,
                    feature_set = None
                )

    def add_dummy_operation(self):
        # use a valid operation spec contained in the test folder
        op_spec_file = os.path.join(
            settings.BASE_DIR, 
            'api', 
            'tests', 
            'operation_test_files',
            'valid_operation.json'
        )
        d=read_operation_json(op_spec_file)
        d['id'] = str(uuid.uuid4())
        d['git_hash'] = 'abcd'
        d['repository_url'] = 'https://github.com/some-repo/'
        d['repo_name'] = 'some-repo'
        op_serializer = validate_operation(d)

        # need to make a directory with dummy files to use the 
        # `save_operation` function
        dummy_dir_path = os.path.join('/tmp', 'dummy_op')
        try:
            os.mkdir(dummy_dir_path)
        except OSError as ex:
            if ex.errno == errno.EEXIST:
                pass
            else:
                raise Exception('Failed to create directory at {p}'.format(p=dummy_dir_path))
        op = op_serializer.get_instance()
        op_data = OperationSerializer(op).data
        save_operation(op_data, dummy_dir_path, True)
        OperationDbModel.objects.create(id=op.id, name=op.name)
        
        # use a valid operation spec contained in the test folder
        op_spec_file = os.path.join(
            settings.BASE_DIR, 
            'api', 
            'tests', 
            'operation_test_files',
            'valid_workspace_operation.json'
        )
        d=read_operation_json(op_spec_file)
        d['id'] = str(uuid.uuid4())
        d['git_hash'] = 'abcd'
        d['repository_url'] = 'https://github.com/some-repo/'
        d['repo_name'] = 'some-repo'
        op_serializer = validate_operation(d)

        # need to make a directory with dummy files to use the 
        # `save_operation` function
        dummy_dir_path = os.path.join('/tmp', 'dummy_op2')
        try:
            os.mkdir(dummy_dir_path)
        except OSError as ex:
            if ex.errno == errno.EEXIST:
                pass
            else:
                raise Exception('Failed to create directory at {p}'.format(p=dummy_dir_path))
        op = op_serializer.get_instance()
        op_data = OperationSerializer(op).data
        save_operation(op_data, dummy_dir_path, True)
        OperationDbModel.objects.create(id=op.id, name=op.name)

    def handle(self, *args, **options):
        self.populate_users()
        self.populate_workspaces()
        self.populate_resources()
        self.add_metadata_to_resources()
        self.add_resources_to_workspace()
        self.add_dummy_operation()
