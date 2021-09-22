import os
import logging
from datetime import timedelta

from django.core.exceptions import ImproperlyConfigured
from django.conf import global_settings
from django.utils.module_loading import import_string

from dotenv import load_dotenv

from .settings_helpers import get_env

logger = logging.getLogger(__name__)

load_dotenv()

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# A directory where we store user data, etc. Outside of the source tree!
DATA_DIR = get_env('DATA_DIR')

# double-check that the data dir exists:
if not os.path.exists(DATA_DIR):
    raise ImproperlyConfigured('There needs to be a directory located at {d}'
        ' for user and operation data.'.format(d=DATA_DIR)
    )

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = [x for x in os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',') if len(x) > 0]

CORS_ORIGIN_ALLOW_ALL = False
CORS_ORIGIN_WHITELIST = [
    x for x in os.environ.get('DJANGO_CORS_ORIGINS', '').split(',') if len(x) > 0
]
CORS_EXPOSE_HEADERS = ['Content-Disposition']

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
    ],
    'PAGE_SIZE': 50
}

# settings for the DRF JWT app:
SIMPLE_JWT = {
    'USER_ID_FIELD': 'user_uuid',
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30)
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
# DON'T CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. THIS NEEDS TO STAY
# IN-SYNC WITH THE DOCKER-COMPOSE YAML
PENDING_FILES_DIR = os.path.join(DATA_DIR, 'pending_user_uploads')
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
# START Parameters for configuring the cloud environment
###############################################################################

# For consistent reference, define the cloud platforms
GOOGLE = 'GOOGLE'

# include any cloud platforms that are implemented in this list.
AVAILABLE_CLOUD_PLATFORMS = [GOOGLE,]

# get the requested platform from the environment variables and ensure 
# that it's valid
CLOUD_PLATFORM = get_env('CLOUD_PLATFORM')
if not CLOUD_PLATFORM in AVAILABLE_CLOUD_PLATFORMS:
    raise ImproperlyConfigured('Requesting a platform ({p}) that is not implemented.'
        ' Please choose from: {x}'.format(
            x =', '.join(AVAILABLE_CLOUD_PLATFORMS),
            p = CLOUD_PLATFORM
        )
    )

# "name" the available remote job runners that are implemented for consistent reference
CROMWELL = 'CROMWELL'
AVAILABLE_REMOTE_JOB_RUNNERS = [CROMWELL,]

# check that we wish to use the remote job runners:
enable_remote_jobs_str = get_env('ENABLE_REMOTE_JOB_RUNNERS')
if enable_remote_jobs_str == 'yes':
    ENABLE_REMOTE_JOBS = True
else:
    ENABLE_REMOTE_JOBS = False

REQUESTED_REMOTE_JOB_RUNNERS = None
if ENABLE_REMOTE_JOBS:
    # read the requested job runners from the environment variables. Check they're ok:
    REQUESTED_REMOTE_JOB_RUNNERS = [x.strip() for x in get_env('REMOTE_JOB_RUNNERS').split(',')]
    set_diff = set(REQUESTED_REMOTE_JOB_RUNNERS).difference(set(AVAILABLE_REMOTE_JOB_RUNNERS))
    if len(set_diff) > 0:
        raise ImproperlyConfigured('The following remote job runners were requested: {x}. However,'
            ' they have not been implemented as determined by the settings.AVAILABLE_REMOTE_JOB_RUNNERS'
            ' variable, which is: {y}'.format(
                x = ','.join(set_diff),
                y = ','.join(AVAILABLE_REMOTE_JOB_RUNNERS)
            )
        )
    
###############################################################################
# END Parameters for configuring the cloud environment
###############################################################################


###############################################################################
# START Parameters for configuring resource storage
###############################################################################

LOCAL = 'local'
REMOTE = 'remote'

# map to the implementing classes. For the remote jobs, we have to reference
# the cloud environment to get the implementing class.
# For each cloud environment, we only allow certain storage backends. For example,
# if we are on GCP, we don't allow AWS S3 storage backend (for simplicity)
# Additionally, if we have chosen to use remote job runners, we will REQUIRE
# that the corresponding bucket storage is used for the backend
AVAILABLE_STORAGE_BACKENDS = [LOCAL, REMOTE]
STORAGE_LOCATION = get_env('STORAGE_LOCATION')
if not (STORAGE_LOCATION in AVAILABLE_STORAGE_BACKENDS):
    raise ImproperlyConfigured('The STORAGE_LOCATION environment'
        ' variable must be one of: {opts}'.format(
            opts = ', '.join([LOCAL, REMOTE])
        )
    )

if ENABLE_REMOTE_JOBS and (STORAGE_LOCATION==LOCAL):
    raise ImproperlyConfigured('Since you enabled remote jobs, you must choose'
        ' remote storage. Edit your environment variables.'
    )

# In the case of remote storage backends (e.g. buckets), we want the ability
# to locally cache the files for faster access.  Files in this directory
# are temporary and will be removed after some period of inactivity
# DON'T CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. THIS NEEDS TO STAY
# IN-SYNC WITH THE DOCKER-COMPOSE YAML
RESOURCE_CACHE_DIR = os.path.join(DATA_DIR, 'resource_cache')
if not os.path.exists(RESOURCE_CACHE_DIR):
    raise ImproperlyConfigured('There should be a directory at {d}. Ideally, this'
        ' directory should persist by making use of docker volumes. This preserves'
        ' the application state in case of API changes and restarts.'.format(
            d = RESOURCE_CACHE_DIR
        )
    )

# How long should the files be kept in the local cache.
# Check the functions for periodic tasks to see how this
# parameter is used.
RESOURCE_CACHE_EXPIRATION_DAYS = 2


# The maximum size (in bytes) to allow "direct" downloads from the API.
# If the file exceeds this, we ask the user to download in another way. 
# Most files are small and this will be fine. However, we don't want users
# trying to download BAM or other large files. They can do that with other methods,
# like via Dropbox.
MAX_DOWNLOAD_SIZE_BYTES = float(get_env('MAX_DOWNLOAD_SIZE_BYTES'))

# To sign URLs for download.
# TODO: can we make this a bit more provider-agnostic?
if STORAGE_LOCATION == REMOTE:
    STORAGE_CREDENTIALS = get_env('STORAGE_CREDENTIALS')
else:
    STORAGE_CREDENTIALS = ''
###############################################################################
# END Parameters for configuring resource storage
###############################################################################

###############################################################################
# START Parameters for configuring social authentication/registration
###############################################################################

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

# the name of a directory where new Operation specifications will be cloned
# and staged for ingestion
# DON'T CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. THIS NEEDS TO STAY
# IN-SYNC WITH THE DOCKER-COMPOSE YAML
CLONE_STAGING_DIR = os.path.join(DATA_DIR, 'operation_staging')
if not os.path.exists(CLONE_STAGING_DIR):
    raise ImproperlyConfigured('There should be a directory at {d}. Ideally, this'
        ' directory should persist by making use of docker volumes. This preserves'
        ' the application state in case of API changes and restarts.'.format(
            d = CLONE_STAGING_DIR
        )
    )
# the name of the file that contains the specification for an Operation:
OPERATION_SPEC_FILENAME = 'operation_spec.json'

# a local directory where the various Operations are stashed
# DON'T CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. THIS NEEDS TO STAY
# IN-SYNC WITH THE DOCKER-COMPOSE YAML
OPERATION_LIBRARY_DIR = os.path.join(DATA_DIR, 'operations')
if not os.path.exists(OPERATION_LIBRARY_DIR):
    raise ImproperlyConfigured('There should be a directory at {d}. Ideally, this'
        ' directory should persist by making use of docker volumes. This preserves'
        ' the application state in case of API changes and restarts.'.format(
            d = OPERATION_LIBRARY_DIR
        )
    )
# This is a list of domains from which we will pull repositories
# If the domains are not in this list, then we will block any attempts
# to clone repositories.
ACCEPTABLE_REPOSITORY_DOMAINS = ['github.com',]

###############################################################################
# END Settings for ingestion of Operations
###############################################################################

###############################################################################
# START Settings for Operation executions
###############################################################################

# a directory where the operations will be run-- each execution of an operation
# gets its own sandbox
OPERATION_EXECUTION_DIR = os.path.join(DATA_DIR, 'operation_executions')
if not os.path.exists(OPERATION_EXECUTION_DIR):
    raise ImproperlyConfigured('There should be a directory at {d}.'.format(
            d = OPERATION_EXECUTION_DIR
        )
    )

###############################################################################
# END Settings for Operation executions
###############################################################################

###############################################################################
# START Settings for public datasets
###############################################################################

PUBLIC_DATA_DIR = os.path.join(DATA_DIR, 'public_data')
if not os.path.exists(PUBLIC_DATA_DIR):
    raise ImproperlyConfigured('There should be a directory for public data at {d}.'.format(
            d = PUBLIC_DATA_DIR
        )
    )

###############################################################################
# END Settings for public datasets
###############################################################################


###############################################################################
# START Settings for Dockerhub 
###############################################################################

# the dockerhub username. e.g. if 'xyz', then the image would be available
# from dockerhub at docker.io/xyz/<image>:<tag>
DOCKERHUB_USERNAME = get_env('DOCKERHUB_USERNAME')
DOCKERHUB_PASSWORD = get_env('DOCKERHUB_PASSWORD')

if (len(DOCKERHUB_USERNAME) == 0) or (len(DOCKERHUB_PASSWORD) == 0) :
    raise ImportError('The dockerhub username or password was blank.')

DOCKERHUB_ORG = get_env('DOCKERHUB_ORG')

# If the org was blank, just use the username
if len(DOCKERHUB_ORG) == 0:
    DOCKERHUB_ORG = DOCKERHUB_USERNAME

###############################################################################
# END Settings for Dockerhub
###############################################################################

# Use these values as 'markers' for dataframes/tables that have infinite values.
# Since the data needs to be returned as valid JSON and Inf (and other variants)
# are not permitted
POSITIVE_INF_MARKER = '++inf++'
NEGATIVE_INF_MARKER = '--inf--'


###############################################################################
# START settings/imports for filtering
###############################################################################

# For pagination-- sets up a consistent reference.
PAGE_PARAM = 'page'
PAGE_SIZE_PARAM = 'page_size'

# import all the filtering operations that can be applied when querying for the content
# of data resources
from api.filters import *

###############################################################################
# END settings/imports for filtering
###############################################################################


###############################################################################
# START settings/imports for public data indexing
###############################################################################

# This determines which indexer we are using for the public data.
# See api/public_data/indexers/__init__.py for the implementing classes.
# Specifically, choose one of the keys in INDEXER_CHOICES
# Don't change unless you know what you're doing.
PUBLIC_DATA_INDEXER = 'solr'

###############################################################################
# END settings/imports for public data indexing
###############################################################################