import os
import copy
import logging.config

from django.core.exceptions import ImproperlyConfigured

from .base_settings import * 
print(dir())

# helper function to catch and warn about missing required environment variables
# that are needed for "secret" config variables.
def get_env_value(env_variable):
    try:
      	return os.environ[env_variable]
    except KeyError:
        error_msg = 'Set the {} environment variable'.format(var_name)
        raise ImproperlyConfigured(error_msg)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = get_env_value('DJANGO_SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = []

DATABASES = {
    'default': {
        'ENGINE': get_env_value('DATABASE_ENGINE'),
        'NAME': get_env_value('DATABASE_NAME'),
        'USER': get_env_value('DATABASE_USER'),
        'PASSWORD': get_env_value('DATABASE_PASSWORD'),
        'HOST': get_env_value('DATABASE_HOST'),
        'PORT': get_env_value('DATABASE_PORT'),
    }
}

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

