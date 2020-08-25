import os
import logging

logger = logging.getLogger(__name__)

from django.core.exceptions import ImproperlyConfigured
from django.conf import global_settings
from django.utils.module_loading import import_string

from .settings_helpers import get_env

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = [x for x in os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',') if len(x) > 0]


CORS_ORIGIN_ALLOW_ALL = False
CORS_ORIGIN_WHITELIST = [
    x for x in os.environ.get('DJANGO_CORS_ORIGINS', '').split(',') if len(x) > 0
]

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'api.apps.ApiConfig',
    'corsheaders',
    'social_django',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'mev.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'mev.wsgi.application'


# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# use an alternate user model which has the email as the username
AUTH_USER_MODEL = 'api.CustomUser'


# The location where we will dump the testing database
TESTING_DB_DUMP = os.path.join(BASE_DIR, 'api', 'tests', 'test_db.json')


REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ]
}

# settings for the DRF JWT app:
SIMPLE_JWT = {
    'USER_ID_FIELD': 'user_uuid'
}

###############################################################################
# Parameters for Email functions
###############################################################################

#  All available backends for sending emails:
EMAIL_BACKEND_SELECTIONS = {
    'CONSOLE': 'django.core.mail.backends.console.EmailBackend',
    'GMAIL': 'mev.gmail_backend.GmailBackend'
}

# Users can optionally specify an environment variable 
# to choose their backend.  Defaults to console if not specified.
try:
    EMAIL_BACKEND_CHOICE = os.environ['EMAIL_BACKEND_CHOICE']
except KeyError:
    EMAIL_BACKEND_CHOICE = 'CONSOLE'

# Now that we have the email backend choice, select the class
# string so that the we can properly set the required EMAIL_BACKEND
# django settings variable
try:
    EMAIL_BACKEND = EMAIL_BACKEND_SELECTIONS[EMAIL_BACKEND_CHOICE]
except KeyError:
    raise ImproperlyConfigured('The email backend specified must be from'
        ' the set: {options}'.format(
            options = ', '.join(EMAIL_BACKEND_SELECTIONS.keys())
        )
    )

# Import the module to test that any dependencies (i.e. credentials)
# are correctly specified as environment variables:
import_string(EMAIL_BACKEND)

# When emails are sent, this will be the "From" field
# If None, emails are sent as ""
FROM_EMAIL = os.environ.get('FROM_EMAIL', None)

###############################################################################
# END Parameters for Email functions
###############################################################################

# The location of the mkdocs YAML configuration file
MAIN_DOC_YAML = os.path.join(BASE_DIR, 'api', 'docs', 'mkdocs.yml')


# A directory where we hold user uploads while they are validated.
# After validation, they are moved to a users' own storage
PENDING_FILES_DIR = os.path.join(BASE_DIR, 'pending_user_uploads')
if not os.path.exists(PENDING_FILES_DIR):
    raise ImproperlyConfigured('Please create a directory for the'
    ' pending uploaded files at {path}.'.format(
        path = PENDING_FILES_DIR)
    )

# A local directory to be used as a tmp dir
# Don't write to /tmp since we can't 
TMP_DIR = '/tmp'
if not os.path.exists(TMP_DIR):
    raise ImproperlyConfigured('Please ensure there exists a'
    ' temporary directory for files at {path}.'.format(
        path = TMP_DIR)
    )  

# change the class that handles the direct file uploads.  This provides a mechanism
# to query for upload progress.
FILE_UPLOAD_HANDLERS = ['mev.upload_handler.UploadProgressCachedHandler',] + \
    global_settings.FILE_UPLOAD_HANDLERS

# We use Redis to manage cache and celery queues.
REDIS_HOST = get_env('REDIS_HOST')
REDIS_BASE_LOCATION = 'redis://{redis_host}:6379'.format(redis_host=REDIS_HOST)

###############################################################################
# Parameters for Redis-based cache
###############################################################################
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': '%s/1' % REDIS_BASE_LOCATION,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient'
        },
        'KEY_PREFIX': 'mev'
    }
}

###############################################################################
# Parameters for Celery queueing
###############################################################################
CELERY_BROKER_URL = REDIS_BASE_LOCATION
CELERY_RESULT_BACKEND = REDIS_BASE_LOCATION
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

# Import the logging config:
from mev import base_logging_config as log_config


###############################################################################
# Parameters for domains and front-end URLs
###############################################################################

# For some of the auth views, various links (sent via email) such as for account
# activation, will direct users to the front-end.  There, the front-end will 
# grab the important components like the token, and send them to the backend, hitting
# the usual API endpoints.

FRONTEND_DOMAIN = get_env('FRONTEND_DOMAIN')
BACKEND_DOMAIN = get_env('BACKEND_DOMAIN')
SITE_NAME = get_env('SITE_NAME')

# Note that the leading "#" is used for setting up the route
# in the front-end correctly.
ACTIVATION_URL = '#/activate/{uid}/{token}'
RESET_PASSWORD_URL = '#/reset-password/{uid}/{token}'


###############################################################################
# END Parameters for domains and front-end URLs
###############################################################################

###############################################################################
# START Parameters for configuring resource storage
###############################################################################

AVAILABLE_STORAGE_BACKENDS = {
    'local': 'api.storage_backends.local.LocalStorage',
    'google': 'api.storage_backends.google_cloud.GoogleBucketStorage'
}

STORAGE_LOCATION = get_env('STORAGE_LOCATION')
if STORAGE_LOCATION in AVAILABLE_STORAGE_BACKENDS:
    RESOURCE_STORAGE_BACKEND = AVAILABLE_STORAGE_BACKENDS[STORAGE_LOCATION]
else:
    raise ImproperlyConfigured('Please use on of the following for specifying'
        ' the storage backend: {csv}'.format(
            csv=','.join(AVAILABLE_STORAGE_BACKENDS.keys())
        )
    )

# import the storage backend to ensure we have set the proper environment variables
# and instantiate an instance of the storage backend
RESOURCE_STORAGE_BACKEND = import_string(RESOURCE_STORAGE_BACKEND)()

# In the case of remote storage backends (e.g. buckets), we want the ability
# to locally cache the files for faster access.  Files in this directory
# are temporary and will be removed after some period of inactivity
RESOURCE_CACHE_DIR = os.path.join(BASE_DIR, 'resource_cache')
if not os.path.exists(RESOURCE_CACHE_DIR):
    os.makedirs(RESOURCE_CACHE_DIR)

# How long should the files be kept in the local cache.
# Check the functions for periodic tasks to see how this
# parameter is used.
RESOURCE_CACHE_EXPIRATION_DAYS = 2

###############################################################################
# END Parameters for configuring resource storage
###############################################################################



###############################################################################
# START Parameters for configuring social authentication/registration
###############################################################################

GOOGLE = 'GOOGLE'

try:
    SOCIAL_BACKENDS = os.environ['SOCIAL_BACKENDS']
    SOCIAL_BACKENDS = [x.strip() for x in SOCIAL_BACKENDS.split(',')]
except KeyError as ex:
    logger.info('No social authentication backends specified')

# They keys of this should match the values of the comma-delimited list
# provided in SOCIAL_BACKENDS.  Each key points at a specific backend.
IMPLEMENTED_SOCIAL_BACKENDS = {
    GOOGLE:'social_core.backends.google.GoogleOAuth2'
}

AUTHENTICATION_BACKENDS = []
for provider in SOCIAL_BACKENDS:
    try:
        backend = IMPLEMENTED_SOCIAL_BACKENDS[provider]
        AUTHENTICATION_BACKENDS.append(backend)
    except KeyError as ex:
        raise ImproperlyConfigured('Could not find an appropriate'
            ' social auth backend implementation for the provider'
            ' identified by: {provider}.  Available implementations'
            ' provided for {options}'.format(
                provider = provider,
                options = ','.join(IMPLEMENTED_SOCIAL_BACKENDS.keys())
            )
        )
    
# required for usual username/password authentication:
AUTHENTICATION_BACKENDS.append('django.contrib.auth.backends.ModelBackend')

###############################################################################
# END Parameters for configuring social authentication/registration
###############################################################################

# For remote services (like checking auth with google), how many 
# times should be attempt to communicate before failing:
MAX_RETRIES = 3


###############################################################################
# START Hooks/setup for Sentry (if used)
###############################################################################

USING_SENTRY = False # by default, do NOT enable sentry
SENTRY_URL = get_env('SENTRY_URL')

if ( (len(SENTRY_URL) > 0) & (SENTRY_URL.startswith('http')) ):
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration
    
    sentry_sdk.init(
        dsn=SENTRY_URL,
        integrations=[DjangoIntegration(), CeleryIntegration()],

        # If you wish to associate users to errors (assuming you are using
        # django.contrib.auth) you may enable sending PII data.
        send_default_pii=True
    )

    USING_SENTRY = True

###############################################################################
# END Hooks/setup for Sentry (if used)
###############################################################################


###############################################################################
# START Settings for ingestion of Operations
###############################################################################

# the name of the file that contains the specification for an Operation:
OPERATION_SPEC_FILENAME = 'operation_spec.json'

# a local directory where the various Operations are stashed
OPERATION_LIBRARY_DIR = os.path.join(BASE_DIR, 'operations')
if not os.path.exists(OPERATION_LIBRARY_DIR):
    os.makedirs(OPERATION_LIBRARY_DIR)

###############################################################################
# END Settings for ingestion of Operations
###############################################################################