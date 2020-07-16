import copy
import logging.config

from .settings_helpers import get_env

SECRET_KEY = get_env('DJANGO_SECRET_KEY')

from .base_settings import * 

DEBUG = True

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
