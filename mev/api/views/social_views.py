import logging

from django.conf import settings

from social_django.utils import psa
from social_core.actions import do_auth as social_core_do_auth


logger = logging.getLogger(__name__)

@psa()
def get_auth_url(request, backend):
    '''
    Returns the initial url to the OAuth2 provider's auth page, e.g. 
    {
        "url": "https://accounts.google.com/o/oauth2/auth?client_id=...&redirect_uri=...&state=...&response_type=code...
    }
    The Oauth2 provider is identified by the `backend` string.
    Note that due to the function signature expected by the `psa` decorator, we
    don't use a class-based view.
    Finally, despite no explicit use of the `backend` arg (a string), the `psa` 
    decorator takes that backend string and attaches
    the proper 'backend' to the request instance so that the remainder
    of the registration flow can happen in social_django
    '''
    return social_core_do_auth(request.backend)