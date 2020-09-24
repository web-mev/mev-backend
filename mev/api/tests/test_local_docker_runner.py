import unittest
import unittest.mock as mock
import os
import json
import copy
import uuid
import shutil

from django.core.exceptions import ImproperlyConfigured

from api.tests.base import BaseAPITestCase
from api.utilities.operations import read_operation_json
from api.runners.local_docker import LocalDockerRunner
from api.models import Resource

# the api/tests dir
TESTDIR = os.path.dirname(__file__)
TESTDIR = os.path.join(TESTDIR, 'operation_test_files')

class LocalDockerRunnerTester(BaseAPITestCase):

    def setUp(self):
        self.filepath = os.path.join(TESTDIR, 'valid_operation.json')

    @mock.patch('api.runners.local_docker.copy_local_resource')
    def test_copy_data_resources(self, mock_copy_local_resource):
        '''
        To execute Operations within a controlled environment, we copy
        the necessary files out of the user's local cache into an execution
        folder. Check that the proper copy calls are made
        '''

        op_data = read_operation_json(self.filepath)
        runner = LocalDockerRunner()

        # this is a mock version of how the inputs would look after they were
        # properly converted for the runner. Note that the keys below need
        # to match those in the mock operation file (location at self.filepath)
        arg_dict = {
            'count_matrix': '/path/to/local/cache/foo.tsv',
            'p_val': 0.05
        }
        exec_dir = '/some/dir'
        runner._copy_data_resources(exec_dir, op_data, arg_dict)
        self.assertEqual(arg_dict['count_matrix'], os.path.join(exec_dir, 'foo.tsv'))

    @mock.patch('api.runners.local_docker.OperationRunner.CONVERTER_FILE', 
        new_callable=mock.PropertyMock, 
        return_value='bad_converters.json')
    def test_handles_bad_converter_gracefully(self, mock_OperationRunner):
        '''
        In the case that a converter class is not found for the input, see that we
        handle this error appropriately.
        '''
        # need a resource to populate the field
        all_r = Resource.objects.all()
        r = all_r[0]
        inputs = {
            'count_matrix': str(r.id),
            'p_val': 0.05
        }
        runner = LocalDockerRunner()
        with self.assertRaises(Exception):
            runner._map_inputs(TESTDIR, inputs)