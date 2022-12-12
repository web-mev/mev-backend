import logging.config

from .settings_helpers import get_env

from .base_settings import *

SECRET_KEY = get_env('DJANGO_SECRET_KEY')

DEBUG = True

# for dev work, just use the local memory cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'
    }
}

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

###############################################################################
# START logging settings for dev
###############################################################################
# If desired, modify `LOGGING` to customize beyond the basic console logging 
# created in base_settings.py

# Register the logging config:
logging.config.dictConfig(LOGGING)

###############################################################################
# END logging settings
###############################################################################
