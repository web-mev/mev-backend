from sentry_sdk import capture_message
from api.utilities.email_utils import send_email_to_admins


def alert_admins(msg):
    '''
    A function to be called when an error occurs that is not necessarily
    "fatal", but needs to be quickly handled or investigated
    '''
    # log to sentry
    capture_message(msg)
    send_email_to_admins(msg)