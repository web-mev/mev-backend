import logging
import os
import sys

from django.apps import AppConfig

logger = logging.getLogger(__name__)

class ApiConfig(AppConfig):
    name = 'api'  
