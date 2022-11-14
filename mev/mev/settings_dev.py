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

# Change the LOGLEVEL env variable if you want logging
# different than INFO:
LOGLEVEL = os.environ.get('LOGLEVEL', 'info').upper()
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level':  LOGLEVEL,
    },
}

# finally, register this config:
logging.config.dictConfig(LOGGING)
