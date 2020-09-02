import unittest
import unittest.mock as mock
import os
import json
import copy
import uuid
import shutil

from api.utilities.operations import read_operation_json

# the api/tests dir
TESTDIR = os.path.dirname(__file__)
TESTDIR = os.path.join(TESTDIR, 'operation_test_files')

class OperationUtilsTester(unittest.TestCase):

    def setUp(self):
        self.filepath = os.path.join(TESTDIR, 'valid_operation.json')
        fp = open(self.filepath)
        self.valid_dict = json.load(fp)
        fp.close()

    @mock.patch('api.utilities.operations.read_local_file')
    def test_read_operation_json(self, mock_read_local_file):

        # test that a properly formatted file returns 
        # a dict as expected:

        fp = open(self.filepath)
        mock_read_local_file.return_value = fp
        d = read_operation_json(self.filepath)
        self.assertDictEqual(d, self.valid_dict)