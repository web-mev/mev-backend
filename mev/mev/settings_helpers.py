import os
from django.core.exceptions import ImproperlyConfigured

def get_env(variable_name):
    '''
    A helper function for loading required environment variables
    and issuing error messages
    '''
    try:
        return os.environ[variable_name]
    except KeyError as ex:
        raise ImproperlyConfigured('You need to specify the {var}'
            ' environment variable.'.format(var=variable_name)
        )
