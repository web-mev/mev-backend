import json
import logging
from collections import OrderedDict

from django.core.paginator import Paginator, Page
from django.conf import settings

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .base import DataResource
from api.exceptions import NonIterableContentsException

JSON = 'json'

logger = logging.getLogger(__name__)


class JsonArrayPage(Page):
    '''
    Overrides some methods of the django.core.paginator.Page
    class. The default version does a cast to a list, which is a problem
    when the "query set" is a dataframe instead of a QuerySet instance
    '''
    def __getitem__(self, index):
        if not isinstance(index, (int, slice)):
            raise TypeError(
                'Page indices must be integers or slices, not %s.'
                % type(index).__name__
            )
        return self.object_list[index]        

class JsonObjectPage(Page):
    def __getitem__(self, index):
        keys = list(self.object_list.keys())
        #self.object_list = list(self.object_list)
        return self.object_list[keys[index]]

class JsonResourcePaginator(Paginator):
    '''
    This overrides the default Django paginator, which
    typically expects to deal with a database query (a QuerySet).

    Dataframes are list-like (sort of...) but the problem is that
    the default django paginator ultimately does a cast to a list. When you 
    cast a pandas dataframe as a list, you only get a list of the
    column names, NOT a list of the "records" (rows).

    The django default Paginator mentions using the _get_page method as a
    way to override the django.core.paginator.Page class (which is where the
    cast occurs). By overriding that method, we can make our own Page-like
    class. 

    Finally, this class can be provided to a subclass of DRF's Paginator
    classes. 
    '''
    def page(self, number):
        """Return a Page object for the given 1-based page number."""
        number = self.validate_number(number)
        bottom = (number - 1) * self.per_page
        top = bottom + self.per_page
        if top + self.orphans >= self.count:
            top = self.count
        if type(self.object_list) == list:
            return JsonArrayPage(self.object_list[bottom:top], number, self)
        else:
            raise NonIterableContentsException()

class JsonResourcePageNumberPagination(PageNumberPagination):
    django_paginator_class = JsonResourcePaginator
    page_size_query_param = settings.PAGE_SIZE_PARAM

    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('count', self.page.paginator.count),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('results', data)
        ]))


class JsonResource(DataResource):

    ACCEPTABLE_EXTENSIONS = [JSON]
    DESCRIPTION = 'A JSON-format file.'

    @staticmethod
    def get_paginator():
        return JsonResourcePageNumberPagination()

    def performs_validation(self):
        '''
        Since we have methods to validate JSON-based DataResource types, we 
        override this method and return True, which indicates that we CAN
        perform validation.
        '''
        return True

    def validate_type(self, resource_path):

        try:
            logger.info('Using python-native JSON loader to read resource: {p}'.format(
                p = resource_path
            ))
            j = json.load(open(resource_path))
            logger.info('Successfully parsed {p} as JSON.'.format(
                p = resource_path
            ))
            return (True, None)
        except json.decoder.JSONDecodeError as ex:
            logger.info('Failed to parse JSON-based resource.')
            return (False, 'There was an issue with the JSON formatting.'
                ' The reported error was: {ex}'.format(ex=ex)
            )
        except Exception as ex:
            logger.info('Parsing a JSON resource raised an unexpected exception.'
                ' Exception was: {ex}'.format(ex=ex)
            )
            return (False, 'There was an unexpected encountered when attempting'
                ' to parse the file was JSON. The reported error was: {ex}'.format(ex=ex)
            )

    def extract_metadata(self, resource_path, parent_op_pk=None):
        # call the super method to initialize the self.metadata
        # dictionary
        super().setup_metadata()

        # now add the information to self.metadata:
        if parent_op_pk:
            self.metadata[DataResource.PARENT_OP] = parent_op_pk
        return self.metadata


    def get_contents(self, resource_path, query_params={}):

        try:
            logger.info('Using python-native JSON loader to read resource: {p}'.format(
                p = resource_path
            ))
            j = json.load(open(resource_path))
            return j
        except Exception as ex:
            logger.info('Failed to load JSON resource. Error was {ex}'.format(ex=ex))
            raise ex
