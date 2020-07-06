import os
import copy
import logging.config

from django.core.exceptions import ImproperlyConfigured

from .base_settings import * 

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = get_env('DJANGO_SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# TODO get the hosts in here.
ALLOWED_HOSTS = []

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': get_env('DB_NAME'),
        'USER': get_env('DB_USER'),
        'PASSWORD': get_env('DB_PASSWD'),
        'HOST': get_env('DB_HOST'),
        'PORT': int(get_env('DB_PORT')),
    }
}

###############################################################################
# START Check for production-specific settings/params
###############################################################################
if EMAIL_BACKEND_CHOICE == 'CONSOLE':
    raise ImproperlyConfigured('In production you cannot use the console email'
        ' backend, as it does not actually send email!'
)
###############################################################################
# END Check for production-specific settings/params
###############################################################################




###############################################################################
# START logging settings
###############################################################################

# setup some logging options for production:
production_config_dict = copy.deepcopy(log_config.base_logging_config_dict)

# make changes to the default logging dict here:

# Add sentry handler:
production_config_dict['handlers']['sentry'] = {
    'level': 'WARNING',
    'class': 'raven.contrib.django.raven_compat.handlers.SentryHandler',
},

# add that sentry handler to the loggers:
production_config_dict['loggers']['']['handlers'].append('sentry')
production_config_dict['loggers']['api']['handlers'].append('sentry')

# finally, register this config:
logging.config.dictConfig(production_config_dict)

###############################################################################
# END logging settings
###############################################################################
