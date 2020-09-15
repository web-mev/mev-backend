import unittest
import unittest.mock as mock
import os
import json
import copy
import uuid
import shutil

from django.conf import settings

from api.serializers.operation_input import OperationInputSerializer
from api.serializers.operation import OperationSerializer
from api.data_structures import Operation
from api.models import Operation as OperationDbModel
from api.runners import AVAILABLE_RUN_MODES
from api.utilities.ingest_operation import read_operation_json, \
    add_required_keys_to_operation, \
    validate_operation, \
    perform_operation_ingestion, \
    save_operation, \
    retrieve_repo_name

# the api/tests dir
TESTDIR = os.path.dirname(__file__)
TESTDIR = os.path.join(TESTDIR, 'operation_test_files')

class OperationIngestionTester(unittest.TestCase):

    def setUp(self):
        self.filepath = os.path.join(TESTDIR, 'valid_operation.json')
        fp = open(self.filepath)
        self.valid_dict = json.load(fp)
        fp.close()

    def test_update_op_dict(self):
        '''
        Tests that the expected keys are added when we use the 
        add_required_keys_to_operation function
        '''
        d = copy.deepcopy(self.valid_dict)
        add_required_keys_to_operation(d, abc=1, xyz='foo')
        self.assertTrue(d['abc'] == 1)
        self.assertTrue(d['xyz'] == 'foo')

    @mock.patch('api.utilities.ingest_operation.check_required_files')
    @mock.patch('api.utilities.ingest_operation.save_operation')
    @mock.patch('api.utilities.ingest_operation.retrieve_commit_hash')
    @mock.patch('api.utilities.ingest_operation.clone_repository')
    @mock.patch('api.utilities.ingest_operation.read_operation_json')
    @mock.patch('api.utilities.ingest_operation.shutil')
    def test_operation_validates(self, 
        mock_shutil,
        mock_read_operation_json, 
        mock_clone_repository,
        mock_retrieve_commit_hash,
        mock_save_operation,
        mock_check_required_files):

        mock_read_operation_json.return_value = self.valid_dict
        mock_hash = 'abcd'
        mock_dir = '/some/mock/staging/dir'
        mock_clone_repository.return_value = mock_dir
        mock_retrieve_commit_hash.return_value = 'abcd'
        repo_url = 'http://github.com/some-repo/'

        n0 = len(OperationDbModel.objects.all())

        op_uuid = uuid.uuid4()
        o = OperationDbModel.objects.create(id=str(op_uuid))
        n1 = len(OperationDbModel.objects.all())
        n2 = len(OperationDbModel.objects.filter(active=True))
        self.assertEqual(n1-n0,1)

        perform_operation_ingestion(
            repo_url, 
            str(op_uuid)
        )

        mock_clone_repository.assert_called_with(repo_url)
        mock_retrieve_commit_hash.assert_called_with(mock_dir)
        mock_save_operation.assert_called()
        mock_shutil.rmtree.assert_called_with(mock_dir)

        n3 = len(OperationDbModel.objects.filter(active=True))
        self.assertEqual(n3-n2,1)

    def test_save_operation(self):
        op_input_dict = {
            'description': 'The filtering threshold for the p-value',
            'name': 'P-value threshold:',
            'required': False,
            'spec': {
                'attribute_type': 'BoundedFloat',
                'min': 0.0,
                'max': 1.0,
                'default': 0.05
            }
        }
        op_input = OperationInputSerializer(data=op_input_dict).get_instance()
        op_id = str(uuid.uuid4())
        operation_instance = Operation(
            op_id,
            'Some op name',
            'Some op description',
            {
                'p_val': op_input,
            },
            {},
            AVAILABLE_RUN_MODES[0],
            'http://github.com/some-repo/',
            'abcd'
        )

        # make a dummy git repo:
        dummy_src_path = os.path.join(settings.BASE_DIR, 'test_dummy_dir')
        os.mkdir(dummy_src_path)

        # add some files to that dummy dir:
        all_files = []
        path_template = os.path.join(dummy_src_path, 'f{idx}.txt')
        for i in range(2):
            p = path_template.format(idx=i)
            with open(p, 'w') as fout:
                fout.write('something...%d' % i)
            all_files.append(p)

        # add a hidden file:
        hidden_path = os.path.join(dummy_src_path, '.my_hidden.txt')
        with open(hidden_path, 'w') as fout:
            fout.write('some content')
        all_files.append(hidden_path)

        # the expected final dir-- need to ensure it was not 
        # already present
        expected_final_dir = os.path.join(
            settings.OPERATION_LIBRARY_DIR,
            op_id
        )
        self.assertFalse(os.path.exists(expected_final_dir))

        # call the save function:
        op_data = OperationSerializer(operation_instance).data
        save_operation(op_data, dummy_src_path)
        self.assertTrue(os.path.exists(expected_final_dir))

        # We are expecting to have an operation spec file as well.
        # The repo dir would contain this already, but we need to
        # add one here since this test is skipping the steps that would
        # assert that said file exists.
        all_files.append(os.path.join(
            expected_final_dir, settings.OPERATION_SPEC_FILENAME))

        # now check that the expected files are there
        self.assertCountEqual(
            os.listdir(expected_final_dir), 
            [os.path.basename(x) for x in all_files]
        )

        # cleanup
        shutil.rmtree(expected_final_dir)
        shutil.rmtree(dummy_src_path)

    @mock.patch('api.utilities.ingest_operation.sp')
    def test_repo_name(self, mock_subprocess):
        '''
        Tests that we parse the name of the git repository correctly
        '''
        mock_process = mock.MagicMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b'git@github.com:xyz/some-repo.git\n', b'')
        mock_subprocess.Popen.return_value = mock_process

        n = retrieve_repo_name('/some/dir/.git')
        self.assertEqual(n, 'some-repo')