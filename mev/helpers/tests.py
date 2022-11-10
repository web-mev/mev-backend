import unittest
import uuid

from exceptions import StringIdentifierException

from . import normalize_identifier


class TestHelperFunctions(unittest.TestCase):

    def test_normalize_identifier(self):
        
        s = '9a-9'
        self.assertEqual(s, normalize_identifier(s))

        s = '_a-9'
        self.assertEqual(s, normalize_identifier(s))

        s = '9a 9'
        self.assertEqual('9a_9', normalize_identifier(s))

        s = 'Unnamed: 5'
        self.assertEqual('Unnamed:_5', normalize_identifier(s))

        s = '__xyz___'
        self.assertEqual(s, normalize_identifier(s))

        s = '.abc'
        self.assertEqual(s, normalize_identifier(s))

        s = '-abc'
        self.assertEqual(s, normalize_identifier(s))

        s = str(uuid.uuid4())
        self.assertEqual(s, normalize_identifier(s))

        with self.assertRaises(StringIdentifierException):
            normalize_identifier('a?bc')

        # check that we don't allow non-ascii.
        # We DO allow this for filenames, etc., but 
        # since we rely on R tools, etc. that may not gracefully
        # handle unicode, we disallow identifiers to use those:
        with self.assertRaises(StringIdentifierException):
            normalize_identifier('9教育漢字')

        with self.assertRaises(StringIdentifierException):
            normalize_identifier('ßå')