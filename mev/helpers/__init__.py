import re

from exceptions import StringIdentifierException


def normalize_identifier(original_name):
    '''
    A function to help constrain names by removing 
    spaces and checks that string consists of only
    - characters
    - underscore
    - dots
    '''
    if not type(original_name) is str:
        raise StringIdentifierException(f'The value {original_name}'
            ' was not a string.')
    # first strip surrounding whitespace
    name = original_name.strip()

    # Change whitespace to underscore
    name = name.replace(' ', '_')

    # this pattern requires we start with a valid character that is
    # not a digit. Thus, we don't allow strings like
    # 9a
    # .A
    # -A
    pattern = '^(?!\d|\-|\.)[\.\-\w]*'
    if re.fullmatch(pattern, name):
        return name
    else:
        raise StringIdentifierException(
            f'The name "{original_name}" did not match the'
            ' naming requirements.  Check that it starts with a'
            ' character and only contains characters, numbers,'
            ' and underscores.')