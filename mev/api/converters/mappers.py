import os
import json

from api.exceptions import InputMappingException

class MapConverter(object):
    '''
    A base class for inputs which serve as a proxy for the true inputs.

    An example is when we need multiple genome-specific files (such as for 
    a BWA alignment) and the user simply needs to dictate which genome to use.
    Then, the mapper implementation will take that input (e.g. a string coming from
    an OptionString input type) and return back the relevant info (paths to 
    index files).

    Importantly, the returned values are what populate the 'final' inputs that are used
    to execute the analysis. So, if we are talking about a Cromwell-based job, then those
    files need to be located in a cloud-based bucket already.
    '''
    pass


class SimpleFileBasedMapConverter(MapConverter):
    '''
    A simple implementation where a single key (such as a genome identifier) will be used
    as a lookup to 
    '''

    # the name of the file which will provide the inputs we need. For instance, if we are
    # using this converter to get genome-specific files, then the keys would be the genome
    # identifiers (e.g. Grch38) and the values would be objects themselves
    # It is expected that this file will exist in the repo. Failure to provide that file
    # will raise an exception at runtime 
    MAPPING_FILE = 'input_mapping.json'

    def convert(self, input_key, user_input, op_dir):
        map_file = os.path.join(op_dir, self.MAPPING_FILE)
        if not os.path.exists(map_file):
            raise InputMappingException('Could not locate the input mapping'
                ' file at {p}'.format(p=map_file))
        try:
            mapping_data = json.load(open(map_file))
        except json.decoder.JSONDecodeError as ex:
            raise InputMappingException('Could not use the JSON parser to load'
                ' the input mapping file at {p}. Exception was {ex}'.format(
                    p=map_file,
                    ex = ex
            ))
        
        try:
            return mapping_data[user_input]
        except KeyError as ex:
            raise InputMappingException('No mapping found for key: "{k}". Check'
                ' the mapping file at {p}'.format(
                    p=map_file,
                    k = user_input
            )) 