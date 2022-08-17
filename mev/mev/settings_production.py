import os
import copy
import logging.config

from django.core.exceptions import ImproperlyConfigured

from .base_settings import * 

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = get_env('DJANGO_SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ['EMAIL_HOST']
EMAIL_PORT = os.environ['EMAIL_PORT']
EMAIL_HOST_USER = os.environ['EMAIL_HOST_USER']
EMAIL_HOST_PASSWORD = os.environ['EMAIL_HOST_PASSWORD']
EMAIL_USE_TLS = True

###############################################################################
# START logging settings
###############################################################################

# setup some logging options for production:
production_config_dict = copy.deepcopy(log_config.base_logging_config_dict)

# make changes to the default logging dict here:

# finally, register this config:
logging.config.dictConfig(production_config_dict)

###############################################################################
# END logging settings
###############################################################################
