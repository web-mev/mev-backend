"""
WSGI config for mev project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application
from django.contrib.staticfiles.handlers import StaticFilesHandler

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mev.settings')
from django.conf import settings

if settings.DEBUG:
    # allows us to serve static files from gunicorn in dev
    application = StaticFilesHandler(get_wsgi_application())
else:
    application = get_wsgi_application()
