import logging
import sys

from django.conf import setttings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = ('Sends an email. Typically used for testing that the email backend'
        ' is correctly configured. Only used for simple text emails.'
    )

    def add_arguments(self, parser):

        parser.add_argument(
            '-m',
            '--message',
            required=True,
            help='The message text to send. Keep it simple.'
        )

        parser.add_argument(
            '-s',
            '--subject',
            required=True,
            help='The subject of the email.'
        )

        parser.add_argument(
            '-e',
            '--email_csv'
            required=True,
            help='One or more email addresses as a comma-delimited string'
        )
        
    def handle(self, *args, **options):
        emails = [x.strip() for x in options['email_csv']]
        try:
            send_mail(
                options['subject'],
                options['message'],
                settings.FROM_EMAIL,
                emails,
            )
        except Exception as ex:
            logger.info('Failed to send email: {ex}'.format(ex))
            sys.stderr.write('Failed to send email. See logs')
