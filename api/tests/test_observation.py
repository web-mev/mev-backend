import unittest

from api.data_structures import Observation
from api.exceptions import StringIdentifierException

class TestObservation(unittest.TestCase):

    def test_bad_identifier_raises_exception(self):
        '''
        Test that names with incompatible
        characters are rejected
        '''

        # cannot have strange characters:
        with self.assertRaises(StringIdentifierException):
            o = Observation('a#b')

        # cannot start with a number
        with self.assertRaises(StringIdentifierException):
            o = Observation('9a')

        # Can't start or end with the dash or dot.
        # The question mark is just a "generic" out-of-bound character
        chars = ['-', '.', '?'] 
        for c in chars:
            # cannot start with this char
            test_name = c + 'abc'
            with self.assertRaises(StringIdentifierException):
                o = Observation(test_name)

            # cannot end with this char
            test_name = 'abc' + c
            with self.assertRaises(StringIdentifierException):
                o = Observation(test_name)

    def test_name_with_space_normalized(self):
        o = Observation('A name')
        self.assertEqual(o.id, 'A_name')