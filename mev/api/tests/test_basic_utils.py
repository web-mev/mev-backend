import os
import shutil
import unittest
import unittest.mock as mock

from django.conf import settings

from api.utilities.basic_utils import move_resource, \
    recursive_copy

class TestBasicUtilities(unittest.TestCase):
    '''
    Tests the functions contained in the api.utilities.basic_utils
    module.
    '''

    @mock.patch('api.utilities.basic_utils.os')
    @mock.patch('api.utilities.basic_utils.shutil')
    def test_unique_resource_creation(self, mock_shutil, mock_os):
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

        mock_shutil.move.is_called_with(source, final_dest)

    @mock.patch('api.utilities.basic_utils.os')
    @mock.patch('api.utilities.basic_utils.shutil')
    def test_resource_move(self, mock_shutil, mock_os):
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

    def test_recursive_copy(self):
        # make a tmp dummy folder
        dummy_src_path = os.path.join('/tmp', 'test_dummy_dir')
        os.mkdir(dummy_src_path)

        # add some files to that dummy dir:
        regular_files = []
        path_template = os.path.join(dummy_src_path, 'f{idx}.txt')
        for i in range(2):
            p = path_template.format(idx=i)
            with open(p, 'w') as fout:
                fout.write('something...%d' % i)
            regular_files.append(p)

        # add a hidden file:
        hidden_path = os.path.join(dummy_src_path, '.my_hidden.txt')
        with open(hidden_path, 'w') as fout:
            fout.write('some content')
        hidden_files = [hidden_path]

        all_files = regular_files + hidden_files

        # make sure all the files are there to start with
        self.assertCountEqual(
            os.listdir(dummy_src_path), 
            [os.path.basename(x) for x in all_files]
        )

        # now use the copy. First check that all the files are included
        # if we include the flag to copy the hidden file:
        dummy_dest_path = os.path.join('/tmp', 'test_dest_dir')
        recursive_copy(dummy_src_path, dummy_dest_path, include_hidden=True)
        self.assertCountEqual(
            os.listdir(dummy_dest_path), 
            [os.path.basename(x) for x in all_files]
        )
        shutil.rmtree(dummy_dest_path)
        
        # now leave off the flag which means we do NOT want to copy
        # the hidden file
        recursive_copy(dummy_src_path, dummy_dest_path)
        self.assertCountEqual(
            os.listdir(dummy_dest_path), 
            [os.path.basename(x) for x in regular_files]
        )
        shutil.rmtree(dummy_dest_path)

        # clean up
        shutil.rmtree(dummy_src_path)
