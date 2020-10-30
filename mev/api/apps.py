import logging
import os
import sys

from django.apps import AppConfig


logger = logging.getLogger(__name__)

class ApiConfig(AppConfig):
    name = 'api'

    def ready(self):
        logger.info('Performing consistency checks.')  
        environment = os.environ['ENVIRONMENT']
        if environment != 'prod':
            logger.info('Skip startup checks since not in production')
        else: 
            from api.cloud_backends import perform_startup_checks
            perform_startup_checks()     
