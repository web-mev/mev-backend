import unittest

from api.exceptions import StringIdentifierException
from api.utilities import normalize_identifier

class TestUtilities(unittest.TestCase):

    def test_bad_chars_raises_exception(self):
        '''
        Test that names with incompatible
        characters are rejected when we use the `normalize_identifier`
        function
        '''

        # cannot have strange characters:
        with self.assertRaises(StringIdentifierException):
            o = normalize_identifier('a#b')

        # cannot start with a number
        with self.assertRaises(StringIdentifierException):
            o = normalize_identifier('9a')

        # Can't start or end with the dash or dot.
        # The question mark is just a "generic" out-of-bound character
        chars = ['-', '.', '?'] 
        for c in chars:
            # cannot start with this char
            test_name = c + 'abc'
            with self.assertRaises(StringIdentifierException):
                o = normalize_identifier(test_name)

            # cannot end with this char
            test_name = 'abc' + c
            with self.assertRaises(StringIdentifierException):
                o = normalize_identifier(test_name)

    def test_name_with_space_normalized(self):
        o = normalize_identifier('A name')
        self.assertEqual(o, 'A_name')

        with self.assertRaises(StringIdentifierException):
            o = normalize_identifier('A name?')