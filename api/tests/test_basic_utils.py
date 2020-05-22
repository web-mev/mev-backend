import os
import unittest
import unittest.mock as mock

from api.utilities.basic_utils import move_resource

class TestBasicUtilities(unittest.TestCase):
    '''
    Tests the functions contained in the api.utilities.basic_utils
    module.
    '''

    @mock.patch('api.utilities.basic_utils.os')
    def test_unique_resource_creation(self, mock_os):
        '''
        In the case where there already exists a file with the 
        same name (VERY unlikely), test that we create something
        unique as expected
        '''
        mock_os.path.basename = os.path.basename
        mock_os.path.dirname = os.path.dirname
        path_exists_mock = mock.Mock()
        path_exists_mock.side_effect = [True, True, True, False]
        mock_os.path.exists = path_exists_mock

        dest = '/a/b/c.txt'
        source = '/some/source/file.txt'

        final_dest = move_resource(source, dest)
        expected_final_dest = '/a/b/10c.txt'
        self.assertTrue(final_dest == expected_final_dest)

        mock_os.rename.is_called_with(source, final_dest)

    @mock.patch('api.utilities.basic_utils.os')
    def test_resource_move(self, mock_os):
        '''
        We mock that there was no existing file at the final
        destination (as there will almost certainly be).  Just
        check that things go as planned.
        '''
        mock_os.path.basename = os.path.basename
        mock_os.path.dirname = os.path.dirname
        path_exists_mock = mock.Mock()
        path_exists_mock.side_effect = [True, False]
        mock_os.path.exists = path_exists_mock

        dest = '/a/b/c.txt'
        source = '/some/source/file.txt'

        final_dest = move_resource(source, dest)
        expected_final_dest = '/a/b/c.txt'
        self.assertTrue(final_dest == expected_final_dest)

        mock_os.rename.is_called_with(source, final_dest)