import os
import logging
import base64
import threading

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.core.exceptions import ImproperlyConfigured

from googleapiclient import discovery
from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)

# These are relatively "static"
GMAIL_TOKEN_URI = 'https://oauth2.googleapis.com/token'

# Need full mail scope to write emails:
GMAIL_SCOPES = ["https://mail.google.com/"]

try:
    GMAIL_ACCESS_TOKEN = os.environ['GMAIL_ACCESS_TOKEN']
    GMAIL_REFRESH_TOKEN = os.environ['GMAIL_REFRESH_TOKEN']
    GMAIL_CLIENT_ID = os.environ['GMAIL_CLIENT_ID']
    GMAIL_CLIENT_SECRET = os.environ['GMAIL_CLIENT_SECRET']
except KeyError as ex:
    raise ImproperlyConfigured('Since you are using the Gmail'
        ' backend, you need to specify the following key: {k}'.format(
            k=ex
        )
    )

class GmailBackend(BaseEmailBackend):
    '''
    Uses the Gmail API to send e-mails.

    Requires a GMAIL_CREDENTIALS_FILE be in your Django settings
    '''

    def __init__(self, *args, **kwargs):
        self._lock = threading.RLock()
        super().__init__(*args, **kwargs)

    def get_gmail_service(self):
        logger.info('Establishing the connection to the Gmail API.')
        credentials = Credentials(GMAIL_ACCESS_TOKEN,
                      refresh_token=GMAIL_REFRESH_TOKEN, 
                      token_uri=GMAIL_TOKEN_URI, 
                      client_id=GMAIL_CLIENT_ID, 
                      client_secret=GMAIL_CLIENT_SECRET, 
                      scopes=GMAIL_SCOPES)
        service = discovery.build('gmail', \
            'v1', \
            credentials = credentials, \
            cache_discovery=False
        )
        logger.info('Service created.')
        return service

    def send_messages(self, email_messages):
        '''
        email_messages is a list of django.core.mail.message.EmailMessage
        instances
        '''
        if not email_messages:
            return

        msg_count = 0
        service = self.get_gmail_service()

        with self._lock:
            try:
                for message in email_messages:
                    msg = message.message()
                    msg_data = msg.as_bytes()
                    charset = msg.get_charset().get_output_charset() if msg.get_charset() else 'utf-8'
                    msg_data = base64.urlsafe_b64encode(msg_data).decode(charset)
                    request_body = {'raw': msg_data}
                    sent_message = service.users().messages().send(
                        userId='me', body=request_body).execute()
                    msg_count += 1    
            except Exception as ex:
                logger.error('Failed in sending message.')
                if not self.fail_silently:
                    raise ex
        return msg_count