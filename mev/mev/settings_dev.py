import copy
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

# setup some logging options for production:
dev_config_dict = copy.deepcopy(log_config.base_logging_config_dict)

# make changes to the default logging dict below:

#######

# finally, register this config:
logging.config.dictConfig(dev_config_dict)
