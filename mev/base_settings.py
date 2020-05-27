import os

from django.core.exceptions import ImproperlyConfigured
from django.conf import global_settings

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = []


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
    'api.apps.ApiConfig'
]

MIDDLEWARE = [
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

# A local directory where we store all the user's local files
USER_STORAGE_DIR = os.path.join(BASE_DIR, 'user_resources')
if not os.path.exists(USER_STORAGE_DIR):
    raise ImproperlyConfigured('Please create a directory for the'
    ' users resources at {path}.'.format(
        path = USER_STORAGE_DIR)
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
REDIS_BASE_LOCATION = 'redis://localhost:6379'

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
