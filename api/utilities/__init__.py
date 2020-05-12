import re

import api.exceptions as api_exceptions

def normalize_identifier(original_name):
    '''
    A function to help constrain names by removing 
    spaces and checks that string consists of only
    - alphanumeric
    - underscore
    - period/dot
    - dash
    '''
    regex_pattern = '[a-zA-Z][a-zA-Z0-9-_\.]*\w'
        
    # Replace spaces and dashes with underscores
    if type(original_name) == str:
        new_name = original_name.replace(' ', '_')
    else:
        raise api_exceptions.StringIdentifierException(
            'The name "{original_name}" was not'
            ' a string.'.format(original_name=original_name))

    # We cannot possibly guess what else could be there, so we 
    # check with a regex
    match = re.match(regex_pattern, new_name)
    if match:
        if match.end() == len(new_name):
            return new_name
    raise api_exceptions.StringIdentifierException(
        'The name "{original_name}" did not match the'
        ' naming requirements.  Check that it only contains'
        ' letters, numbers, dashes, underscores, or dot/periods.'
        ' It should match the regex {regex}'.format(
            original_name=original_name,
            regex=regex_pattern))
