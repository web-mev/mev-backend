from django.core.management import call_command
from django.core.management.base import BaseCommand

from django.conf import settings

class Command(BaseCommand):
    help = 'Dumps the data to file for use with testing.'

    def handle(self, *args, **options):
        call_command('dumpdata', 'api', output=settings.TESTING_DB_DUMP)