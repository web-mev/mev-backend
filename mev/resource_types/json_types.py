import json
import logging

from .base import DataResource

JSON = 'json'

logger = logging.getLogger(__name__)

class JsonResource(DataResource):

    ACCEPTABLE_EXTENSIONS = [JSON]
    DESCRIPTION = 'A JSON-format file.'

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


    def get_contents(self, resource_path):

        try:
            logger.info('Using python-native JSON loader to read resource: {p}'.format(
                p = resource_path
            ))
            return json.load(open(resource_path))
        except Exception as ex:
            logger.info('Failed to load JSON resource. Error was {ex}'.format(ex=ex))
            raise ex