import logging
import json


logger = logging.getLogger(__name__)


class JsonConverter(object):

    def convert_output(self, 
        executed_op, user_workspace, output_definition, output_val):

        # output_val is a string (properly escaped, hopefully!) that contains
        # an arbitrary JSON data structure.
        # If `output_val` is not properly formatted json, this will raise
        # an exception which will fail the job.
        return json.loads(output_val)


