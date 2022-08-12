from django.contrib.auth import get_user_model
from django.contrib.auth.management.commands import createsuperuser


class Command(createsuperuser.Command):
    help = 'Create superuser if does not exist already'

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)

    def handle(self, *args, **options):
        user_model = get_user_model()
        if user_model.objects.filter(username=options['username']).exists():
            self.stdout.write('Superuser already exists, not creating')
            return
        super(Command, self).handle(*args, **options)
