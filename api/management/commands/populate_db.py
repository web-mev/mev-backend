from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from api.models import Workspace
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

    def handle(self, *args, **options):
        self.populate_users()
        self.populate_workspaces()