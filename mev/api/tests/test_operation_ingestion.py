import unittest
import unittest.mock as mock
import os
import json
import copy

from api.utilities.ingest_operation import read_operation_json, \
    add_required_keys_to_operation, \
    validate_operation, \
    perform_operation_ingestion

# the api/tests dir
TESTDIR = os.path.dirname(__file__)
TESTDIR = os.path.join(TESTDIR, 'operation_test_files')

class OperationIngestionTester(unittest.TestCase):

    def setUp(self):
        self.filepath = os.path.join(TESTDIR, 'valid_operation.json')
        fp = open(self.filepath)
        self.valid_dict = json.load(fp)
        fp.close()

    @mock.patch('api.utilities.ingest_operation.read_local_file')
    def test_read_operation_json(self, mock_read_local_file):

        # test that a properly formatted file returns 
        # a dict as expected:

        fp = open(self.filepath)
        mock_read_local_file.return_value = fp
        d = read_operation_json(self.filepath)
        self.assertDictEqual(d, self.valid_dict)

    def test_update_op_dict(self):
        
        d = copy.deepcopy(self.valid_dict)
        add_required_keys_to_operation(d, abc=1, xyz='foo')
        self.assertTrue(d['abc'] == 1)
        self.assertTrue(d['xyz'] == 'foo')

    @mock.patch('api.utilities.ingest_operation.clone_repository')
    @mock.patch('api.utilities.ingest_operation.read_operation_json')
    def test_operation_validates(self, mock_read_operation_json, 
        mock_clone_repository):

        mock_read_operation_json.return_value = self.valid_dict
        mock_hash = 'abcd'
        mock_clone_repository.return_value = ('', mock_hash)
        perform_operation_ingestion('http://github.com/some-repo/')
