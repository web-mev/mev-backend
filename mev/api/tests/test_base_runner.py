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
from api.runners.base import OperationRunner
from api.models import Resource

# the api/tests dir
TESTDIR = os.path.dirname(__file__)
TESTDIR = os.path.join(TESTDIR, 'operation_test_files')

class BaseRunnerTester(BaseAPITestCase):

    @mock.patch('api.runners.base.OperationRunner._get_converter_dict')
    @mock.patch('api.runners.base.os.path.exists')
    def test_bad_converter_class(self, mock_os_exists, mock_get_converter_dict):
        '''
        Test that a bad converter class will raise an exception
        '''
        runner = OperationRunner()
        mock_get_converter_dict.return_value = {'a': 'some junk'}
        with self.assertRaises(Exception):
            runner.check_required_files('')


   