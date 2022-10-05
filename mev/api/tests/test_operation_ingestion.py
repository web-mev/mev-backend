import unittest.mock as mock
import os
import json
import copy
import uuid
import shutil

from django.conf import settings

from exceptions import InvalidResourceTypeException, \
    DataStructureValidationException, \
    InvalidRunModeException

from api.serializers.operation import OperationSerializer
from data_structures.operation import Operation
from api.models import Operation as OperationDbModel
from api.utilities.ingest_operation import add_required_keys_to_operation, \
    perform_operation_ingestion, \
    save_operation, \
    retrieve_repo_name, \
    ingest_dir, \
    check_for_operation_resources, \
    validate_operation_spec

from api.tests.base import BaseAPITestCase

# the api/tests dir
TESTDIR = os.path.dirname(__file__)
TESTDIR = os.path.join(TESTDIR, 'operation_test_files')

class OperationIngestionTester(BaseAPITestCase):

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

    @mock.patch('api.utilities.ingest_operation.clone_repository')
    @mock.patch('api.utilities.ingest_operation.requests')
    def test_bad_repository_url(self, mock_requests, mock_clone_repository):
        '''
        Tests where a bad url is provided for the github repo.
        This can either be a url that does not exist OR one that
        does not show up since it's private (we don't allow cloning
        of private repos)
        '''
        mock_response = mock.MagicMock()
        mock_response.status_code == 404
        mock_requests.get.return_value = mock_response
        repo_url = 'http://github.com/some-repo/'

        n0 = len(OperationDbModel.objects.all())

        op_uuid = uuid.uuid4()
        o = OperationDbModel.objects.create(id=str(op_uuid))
        n1 = len(OperationDbModel.objects.all())
        n2 = len(OperationDbModel.objects.filter(active=True))
        self.assertEqual(n1-n0,1)

        with self.assertRaisesRegex(Exception, 'not find'):
            perform_operation_ingestion(
                repo_url, 
                str(op_uuid),
                None # this means no specific commit was requested
            )

        mock_clone_repository.assert_not_called()
        
        n3 = len(OperationDbModel.objects.filter(active=True))
        self.assertEqual(n3-n2,0)

        op = OperationDbModel.objects.get(id=str(op_uuid))
        self.assertFalse(op.successful_ingestion)


    @mock.patch('api.utilities.ingest_operation.prepare_operation')
    @mock.patch('api.utilities.ingest_operation.retrieve_repo_name')
    @mock.patch('api.utilities.ingest_operation.check_required_files')
    @mock.patch('api.utilities.ingest_operation.save_operation')
    @mock.patch('api.utilities.ingest_operation.retrieve_commit_hash')
    @mock.patch('api.utilities.ingest_operation.clone_repository')
    @mock.patch('api.utilities.ingest_operation.checkout_branch')
    @mock.patch('api.utilities.ingest_operation.check_for_repo')
    @mock.patch('api.utilities.ingest_operation.read_operation_json')
    @mock.patch('api.utilities.ingest_operation.shutil')
    def test_operation_validates(self, 
        mock_shutil,
        mock_read_operation_json, 
        mock_check_for_repo,
        mock_checkout_branch,
        mock_clone_repository,
        mock_retrieve_commit_hash,
        mock_save_operation,
        mock_check_required_files,
        mock_retrieve_repo_name,
        mock_prepare_operation):
        '''
        Here, the ingestion request does not include a specific commit, so 
        we ensure that the specific git commit functions are called or not called
        '''

        mock_read_operation_json.return_value = self.valid_dict
        mock_hash = 'abcd'
        mock_dir = '/some/mock/staging/dir'
        mock_clone_repository.return_value = mock_dir
        mock_retrieve_commit_hash.return_value = 'abcd'
        repo_url = 'http://github.com/some-repo/'
        repo_name = 'some-repo'
        mock_retrieve_repo_name.return_value = repo_name

        n0 = len(OperationDbModel.objects.all())

        op_uuid = uuid.uuid4()
        o = OperationDbModel.objects.create(id=str(op_uuid))
        n1 = len(OperationDbModel.objects.all())
        n2 = len(OperationDbModel.objects.filter(active=True))
        self.assertEqual(n1-n0,1)

        perform_operation_ingestion(
            repo_url, 
            str(op_uuid),
            None # this means no specific commit was requested
        )

        mock_clone_repository.assert_called_with(repo_url)
        mock_retrieve_commit_hash.assert_called_with(mock_dir)
        mock_save_operation.assert_called()
        mock_shutil.rmtree.assert_called_with(mock_dir)
        mock_checkout_branch.assert_not_called()

        n3 = len(OperationDbModel.objects.filter(active=True))
        self.assertEqual(n3-n2,1)

        op = OperationDbModel.objects.get(id=op_uuid)
        self.assertFalse(op.workspace_operation)

    @mock.patch('api.utilities.ingest_operation.prepare_operation')
    @mock.patch('api.utilities.ingest_operation.retrieve_repo_name')
    @mock.patch('api.utilities.ingest_operation.check_required_files')
    @mock.patch('api.utilities.ingest_operation.save_operation')
    @mock.patch('api.utilities.ingest_operation.retrieve_commit_hash')
    @mock.patch('api.utilities.ingest_operation.clone_repository')
    @mock.patch('api.utilities.ingest_operation.checkout_branch')
    @mock.patch('api.utilities.ingest_operation.check_for_repo')
    @mock.patch('api.utilities.ingest_operation.read_operation_json')
    @mock.patch('api.utilities.ingest_operation.shutil')
    def test_operation_validates_case2(self, 
        mock_shutil,
        mock_read_operation_json, 
        mock_check_for_repo,
        mock_checkout_branch,
        mock_clone_repository,
        mock_retrieve_commit_hash,
        mock_save_operation,
        mock_check_required_files,
        mock_retrieve_repo_name,
        mock_prepare_operation):
        '''
        Here, we explicitly request a specific commit ID, so different
        functions are called
        '''

        mock_read_operation_json.return_value = self.valid_dict
        mock_hash = 'abcd'
        mock_dir = '/some/mock/staging/dir'
        mock_clone_repository.return_value = mock_dir
        mock_retrieve_commit_hash.return_value = 'abcd'
        repo_url = 'http://github.com/some-repo/'
        repo_name = 'some-repo'
        mock_retrieve_repo_name.return_value = repo_name
        mock_commit_id = 'abcd1234'

        n0 = len(OperationDbModel.objects.all())

        op_uuid = uuid.uuid4()
        o = OperationDbModel.objects.create(id=str(op_uuid))
        n1 = len(OperationDbModel.objects.all())
        n2 = len(OperationDbModel.objects.filter(active=True))
        self.assertEqual(n1-n0,1)

        perform_operation_ingestion(
            repo_url, 
            str(op_uuid),
            mock_commit_id
        )

        mock_clone_repository.assert_called_with(repo_url)
        mock_retrieve_commit_hash.assert_not_called()
        mock_save_operation.assert_called()
        mock_shutil.rmtree.assert_called_with(mock_dir)
        mock_checkout_branch.assert_called_with(mock_dir, mock_commit_id)
        mock_check_for_repo.assert_called_with(repo_url)

        n3 = len(OperationDbModel.objects.filter(active=True))
        self.assertEqual(n3-n2,1)

        op = OperationDbModel.objects.get(id=op_uuid)
        self.assertFalse(op.workspace_operation)

    @mock.patch('api.utilities.ingest_operation.prepare_operation')
    @mock.patch('api.utilities.ingest_operation.retrieve_repo_name')
    @mock.patch('api.utilities.ingest_operation.check_required_files')
    @mock.patch('api.utilities.ingest_operation.save_operation')
    @mock.patch('api.utilities.ingest_operation.retrieve_commit_hash')
    @mock.patch('api.utilities.ingest_operation.clone_repository')
    @mock.patch('api.utilities.ingest_operation.checkout_branch')
    @mock.patch('api.utilities.ingest_operation.check_for_repo')
    @mock.patch('api.utilities.ingest_operation.read_operation_json')
    @mock.patch('api.utilities.ingest_operation.shutil')
    def test_workspace_operation_validates(self, 
        mock_shutil,
        mock_read_operation_json,
        mock_check_for_repo,
        mock_checkout_branch,
        mock_clone_repository,
        mock_retrieve_commit_hash,
        mock_save_operation,
        mock_check_required_files,
        mock_retrieve_repo_name,
        mock_prepare_operation):
        '''
        Here, we do not request a specific commit ID, so different
        functions are called
        '''

        filepath = os.path.join(TESTDIR, 'valid_workspace_operation.json')
        fp = open(filepath)
        op_dict = json.load(fp)
        fp.close()
        mock_read_operation_json.return_value = op_dict
        mock_hash = 'abcd'
        mock_dir = '/some/mock/staging/dir'
        mock_clone_repository.return_value = mock_dir
        mock_retrieve_commit_hash.return_value = 'abcd'
        repo_url = 'http://github.com/some-repo/'
        repo_name = 'some-repo'
        mock_retrieve_repo_name.return_value = repo_name
        mock_commit_id = 'abcdefg1234'

        n0 = len(OperationDbModel.objects.all())

        op_uuid = uuid.uuid4()
        o = OperationDbModel.objects.create(id=str(op_uuid))
        n1 = len(OperationDbModel.objects.all())
        n2 = len(OperationDbModel.objects.filter(active=True))
        self.assertEqual(n1-n0,1)

        perform_operation_ingestion(
            repo_url, 
            str(op_uuid),
            None # this means a specific commit was NOT requested
        )

        mock_clone_repository.assert_called_with(repo_url)
        mock_retrieve_commit_hash.assert_called_with(mock_dir)
        mock_save_operation.assert_called()
        mock_shutil.rmtree.assert_called_with(mock_dir)
        mock_checkout_branch.assert_not_called()
        mock_check_for_repo.assert_called_with(repo_url)

        n3 = len(OperationDbModel.objects.filter(active=True))
        self.assertEqual(n3-n2,1)

        op = OperationDbModel.objects.get(id=op_uuid)
        self.assertTrue(op.workspace_operation)

    @mock.patch('api.utilities.ingest_operation.prepare_operation')
    @mock.patch('api.utilities.ingest_operation.retrieve_repo_name')
    @mock.patch('api.utilities.ingest_operation.check_required_files')
    @mock.patch('api.utilities.ingest_operation.save_operation')
    @mock.patch('api.utilities.ingest_operation.retrieve_commit_hash')
    @mock.patch('api.utilities.ingest_operation.clone_repository')
    @mock.patch('api.utilities.ingest_operation.checkout_branch')
    @mock.patch('api.utilities.ingest_operation.check_for_repo')
    @mock.patch('api.utilities.ingest_operation.read_operation_json')
    @mock.patch('api.utilities.ingest_operation.shutil')
    def test_workspace_operation_validates_case2(self, 
        mock_shutil,
        mock_read_operation_json,
        mock_check_for_repo,
        mock_checkout_branch,
        mock_clone_repository,
        mock_retrieve_commit_hash,
        mock_save_operation,
        mock_check_required_files,
        mock_retrieve_repo_name,
        mock_prepare_operation):
        '''
        Here, we explicitly request a specific commit ID, so different
        functions are called
        '''

        filepath = os.path.join(TESTDIR, 'valid_workspace_operation.json')
        fp = open(filepath)
        op_dict = json.load(fp)
        fp.close()
        mock_read_operation_json.return_value = op_dict
        mock_hash = 'abcd'
        mock_dir = '/some/mock/staging/dir'
        mock_clone_repository.return_value = mock_dir
        mock_retrieve_commit_hash.return_value = 'abcd'
        repo_url = 'http://github.com/some-repo/'
        repo_name = 'some-repo'
        mock_retrieve_repo_name.return_value = repo_name
        mock_commit_id = 'abcdefg1234'

        n0 = len(OperationDbModel.objects.all())

        op_uuid = uuid.uuid4()
        o = OperationDbModel.objects.create(id=str(op_uuid))
        n1 = len(OperationDbModel.objects.all())
        n2 = len(OperationDbModel.objects.filter(active=True))
        self.assertEqual(n1-n0,1)

        perform_operation_ingestion(
            repo_url, 
            str(op_uuid),
            mock_commit_id
        )

        mock_clone_repository.assert_called_with(repo_url)
        mock_retrieve_commit_hash.assert_not_called()
        mock_save_operation.assert_called()
        mock_shutil.rmtree.assert_called_with(mock_dir)
        mock_checkout_branch.assert_called_with(mock_dir, mock_commit_id)
        mock_check_for_repo.assert_called_with(repo_url)

        n3 = len(OperationDbModel.objects.filter(active=True))
        self.assertEqual(n3-n2,1)

        op = OperationDbModel.objects.get(id=op_uuid)
        self.assertTrue(op.workspace_operation)

    @mock.patch('api.utilities.ingest_operation.prepare_operation')
    @mock.patch('api.utilities.ingest_operation.retrieve_repo_name')
    @mock.patch('api.utilities.ingest_operation.check_required_files')
    @mock.patch('api.utilities.ingest_operation.save_operation')
    @mock.patch('api.utilities.ingest_operation.retrieve_commit_hash')
    @mock.patch('api.utilities.ingest_operation.clone_repository')
    @mock.patch('api.utilities.ingest_operation.checkout_branch')
    @mock.patch('api.utilities.ingest_operation.check_for_repo')
    @mock.patch('api.utilities.ingest_operation.read_operation_json')
    @mock.patch('api.utilities.ingest_operation.shutil')
    def test_operation_rejected_for_validation(self, 
        mock_shutil,
        mock_read_operation_json, 
        mock_check_for_repo,
        mock_checkout_branch,
        mock_clone_repository,
        mock_retrieve_commit_hash,
        mock_save_operation,
        mock_check_required_files,
        mock_retrieve_repo_name,
        mock_prepare_operation):
        '''
        Here, leave out the workspace_operation key and check 
        that it will raise an error.
        '''
        j = json.load(open(os.path.join(TESTDIR, 'invalid_operation.json')))
        mock_read_operation_json.return_value = j
        mock_hash = 'abcd'
        mock_dir = '/some/mock/staging/dir'
        mock_clone_repository.return_value = mock_dir
        mock_retrieve_commit_hash.return_value = 'abcd'
        repo_url = 'http://github.com/some-repo/'
        repo_name = 'some-repo'
        mock_retrieve_repo_name.return_value = repo_name

        n0 = len(OperationDbModel.objects.all())

        op_uuid = uuid.uuid4()
        o = OperationDbModel.objects.create(id=str(op_uuid))
        n1 = len(OperationDbModel.objects.all())
        n2 = len(OperationDbModel.objects.filter(active=True))
        self.assertEqual(n1-n0,1)

        with self.assertRaises(DataStructureValidationException):
            perform_operation_ingestion(
                repo_url, 
                str(op_uuid),
                None
            )

        mock_clone_repository.assert_called_with(repo_url)
        mock_retrieve_commit_hash.assert_called_with(mock_dir)
        mock_save_operation.assert_not_called()
        mock_shutil.rmtree.assert_called_with(mock_dir)
        mock_checkout_branch.assert_not_called()
        mock_check_for_repo.assert_called_with(repo_url)

        n3 = len(OperationDbModel.objects.filter(active=True))
        self.assertEqual(n3-n2,0)

    @mock.patch('api.utilities.ingest_operation.prepare_operation')
    @mock.patch('api.utilities.ingest_operation.retrieve_repo_name')
    @mock.patch('api.utilities.ingest_operation.check_required_files')
    @mock.patch('api.utilities.ingest_operation.save_operation')
    @mock.patch('api.utilities.ingest_operation.retrieve_commit_hash')
    @mock.patch('api.utilities.ingest_operation.clone_repository')
    @mock.patch('api.utilities.ingest_operation.checkout_branch')
    @mock.patch('api.utilities.ingest_operation.check_for_repo')
    @mock.patch('api.utilities.ingest_operation.read_operation_json')
    @mock.patch('api.utilities.ingest_operation.shutil')
    def test_operation_rejected_for_bad_formatting(self, 
        mock_shutil,
        mock_read_operation_json, 
        mock_check_for_repo,
        mock_checkout_branch,
        mock_clone_repository,
        mock_retrieve_commit_hash,
        mock_save_operation,
        mock_check_required_files,
        mock_retrieve_repo_name,
        mock_prepare_operation):
        '''
        Here we check that bad formatting in the case of nested objects
        will raise an exception. This stems from a problem where the 'inputs'
        dict was missing a brace. This caused the remaining inputs to appear
        as extra keys of a single input. However, it was valid json so it all
        passed validation. The result was that some of the inputs were missing
        in the final ingested operation spec. The extra keys were silently
        ignored.

        This tests that we raise an exception under these circumstances.
        '''
        j = json.load(open(os.path.join(TESTDIR, 'op_with_bad_formatting.json')))
        mock_read_operation_json.return_value = j
        mock_hash = 'abcd'
        mock_dir = '/some/mock/staging/dir'
        mock_clone_repository.return_value = mock_dir
        mock_retrieve_commit_hash.return_value = 'abcd'
        repo_url = 'http://github.com/some-repo/'
        repo_name = 'some-repo'
        mock_retrieve_repo_name.return_value = repo_name

        n0 = len(OperationDbModel.objects.all())

        op_uuid = uuid.uuid4()
        o = OperationDbModel.objects.create(id=str(op_uuid))
        n1 = len(OperationDbModel.objects.all())
        n2 = len(OperationDbModel.objects.filter(active=True))
        self.assertEqual(n1-n0,1)

        with self.assertRaises(DataStructureValidationException):
            perform_operation_ingestion(
                repo_url, 
                str(op_uuid),
                None
            )

        mock_clone_repository.assert_called_with(repo_url)
        mock_retrieve_commit_hash.assert_called_with(mock_dir)
        mock_save_operation.assert_not_called()
        mock_shutil.rmtree.assert_called_with(mock_dir)
        # no specific commit was passed (None), so this function is not called
        mock_checkout_branch.assert_not_called()
        mock_check_for_repo.assert_called_with(repo_url)

        n3 = len(OperationDbModel.objects.filter(active=True))
        self.assertEqual(n3-n2,0)

    def test_save_operation(self):
        op_input_dict = {
            'description': 'The filtering threshold for the p-value',
            'name': 'P-value threshold:',
            'required': False,
            'converter': 'api.converters.basic_attributes.BoundedFloatAttributeConverter',
            'spec': {
                'attribute_type': 'BoundedFloat',
                'min': 0.0,
                'max': 1.0,
                'default': 0.05
            }
        }
        op_id = str(uuid.uuid4())

        op_dict = {
            'id': op_id,
            'name': 'Some name', 
            'description': 'Here is some description of the process', 
            'inputs': {
                'p_val': op_input_dict
            }, 
            'outputs': {}, 
            'mode': 'local_docker', 
            'workspace_operation': True,
            'git_hash': 'abc123',
            "repository_url": '',
            "repository_name": '',
            "workspace_operation": True
        }

        operation_instance = Operation(op_dict)

        # make a dummy git repo:
        dummy_src_path = os.path.join('/tmp', 'test_dummy_dir')
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
        save_operation(op_data, dummy_src_path, True)
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

    @mock.patch('api.utilities.ingest_operation.sp')
    def test_repo_name_case2(self, mock_subprocess):
        '''
        Tests that we parse the name of the git repository correctly if the url did not have
        the .git suffix. Note that git clone can work with both. Failure to end with '.git' was
        leading to truncated repository names (and hence docker images)
        '''
        mock_process = mock.MagicMock()
        mock_process.returncode = 0
        # Note that the url below does NOT have the '.git' suffix.
        mock_process.communicate.return_value = (b'https://github.com:web-mev/some-repo\n', b'')
        mock_subprocess.Popen.return_value = mock_process

        # since we mock out the subprocess, the arg below doesn't actually matter.
        n = retrieve_repo_name('')
        self.assertEqual(n, 'some-repo')

    @mock.patch('api.utilities.ingest_operation.prepare_operation')
    @mock.patch('api.utilities.ingest_operation.retrieve_repo_name')
    @mock.patch('api.utilities.ingest_operation.check_required_files')
    @mock.patch('api.utilities.ingest_operation.retrieve_commit_hash')
    @mock.patch('api.utilities.ingest_operation.clone_repository')
    @mock.patch('api.utilities.ingest_operation.checkout_branch')
    @mock.patch('api.utilities.ingest_operation.check_for_repo')
    @mock.patch('api.utilities.ingest_operation.read_operation_json')
    @mock.patch('api.utilities.ingest_operation.shutil')
    @mock.patch('api.utilities.ingest_operation.settings')
    def test_operation_overwrite_blocked(self,
        mock_settings,
        mock_shutil,
        mock_read_operation_json, 
        mock_check_for_repo,
        mock_checkout_branch,
        mock_clone_repository,
        mock_retrieve_commit_hash,
        mock_check_required_files,
        mock_retrieve_repo_name,
        mock_prepare_operation):
        '''
        If we do not specifically request that an operation be overwritten,
        we check that the operation is appropriately marked as failed.
        '''
        # make a tmp directory which will act as an existing operation library dir
        mock_ops_dir = '/tmp/some-fake-op-dir'
        os.mkdir(mock_ops_dir)
        mock_settings.OPERATION_LIBRARY_DIR = mock_ops_dir
        mock_settings.OPERATION_SPEC_FILENAME = 'foo'
        # setup the remainder of the mocks
        mock_read_operation_json.return_value = self.valid_dict
        mock_hash = 'abcd'
        mock_dir = '/some/mock/staging/dir'
        mock_clone_repository.return_value = mock_dir
        mock_retrieve_commit_hash.return_value = 'abcd'
        repo_url = 'http://github.com/some-repo/'
        repo_name = 'some-repo'
        mock_retrieve_repo_name.return_value = repo_name

        n0 = len(OperationDbModel.objects.all())

        op_uuid = uuid.uuid4()
        # pretend we had an active model prior to this attempted (but failed)
        # ingestion process
        o = OperationDbModel.objects.create(id=str(op_uuid), 
            active=True,
            successful_ingestion=True)
        n1 = len(OperationDbModel.objects.all())
        n2 = len(OperationDbModel.objects.filter(active=True))
        self.assertEqual(n1-n0,1)

        # create the mock operation dir
        op_dir_path = os.path.join(mock_ops_dir, str(op_uuid))
        os.mkdir(op_dir_path)

        with self.assertRaises(Exception):
            perform_operation_ingestion(
                repo_url, 
                str(op_uuid),
                None
            )

        mock_clone_repository.assert_called_with(repo_url)
        mock_retrieve_commit_hash.assert_called_with(mock_dir)
        mock_shutil.rmtree.assert_called_with(mock_dir)
        mock_checkout_branch.assert_not_called()
        mock_check_for_repo.assert_called_with(repo_url)

        # check that we did NOT add another operation
        n3 = len(OperationDbModel.objects.filter(active=True))
        self.assertEqual(n3-n2,0)

        # If the ingestion failed due to the failure to overwrite,
        # we want to maintain the former operation with that same UUID
        op = OperationDbModel.objects.get(id=op_uuid)
        self.assertTrue(op.successful_ingestion)
        self.assertTrue(op.active)

        # cleanup from this test:
        shutil.rmtree(mock_ops_dir)


    @mock.patch('api.utilities.ingest_operation.prepare_operation')
    @mock.patch('api.utilities.ingest_operation.check_required_files')
    @mock.patch('api.utilities.ingest_operation.read_operation_json')
    @mock.patch('api.utilities.ingest_operation.settings')
    def test_operation_overwrite_allowed(self,
        mock_settings,
        mock_read_operation_json, 
        mock_check_required_files,
        mock_prepare_operation):
        '''
        If we do specifically request that an operation be overwritten,
        we check that everything goes as planned
        '''
        # make a tmp directory which will act as an existing operation library dir
        mock_ops_dir = '/tmp/some-fake-op-dir'
        os.mkdir(mock_ops_dir)

        # also need to make a "real" staging dir so that the 
        # shutil.copytree function works
        mock_staging_dir = '/tmp/some-fake-staging-dir'
        os.mkdir(mock_staging_dir)

        mock_settings.OPERATION_LIBRARY_DIR = mock_ops_dir
        mock_settings.OPERATION_SPEC_FILENAME = 'foo'
        # setup the remainder of the mocks
        mock_read_operation_json.return_value = self.valid_dict
        mock_hash = 'abcd'
        repo_url = 'http://github.com/some-repo/'
        repo_name = 'some-repo'

        n0 = len(OperationDbModel.objects.all())

        op_uuid = uuid.uuid4()
        o = OperationDbModel.objects.create(id=str(op_uuid))
        n1 = len(OperationDbModel.objects.all())
        n2 = len(OperationDbModel.objects.filter(active=True))
        self.assertEqual(n1-n0,1)

        # create the mock operation dir
        op_dir_path = os.path.join(mock_ops_dir, str(op_uuid))
        os.mkdir(op_dir_path)

        ingest_dir(mock_staging_dir, str(op_uuid), mock_hash, repo_name, repo_url, True)

        # check that the overwrite succeeded and the operation is active
        n3 = len(OperationDbModel.objects.filter(active=True))
        self.assertEqual(n3-n2,1)

        # check that it was marked as failed:
        op = OperationDbModel.objects.get(id=op_uuid)
        self.assertTrue(op.successful_ingestion)

        # cleanup from this test:
        shutil.rmtree(mock_ops_dir)
        shutil.rmtree(mock_staging_dir)

    def test_check_for_operation_resources(self):
        '''
        Tests that we get the expected inputs from the operation spec file.
        This should be a subset of the inputs that correspond to user-independent
        OperationResource types.
        '''
        # should only get a single key back 
        p = os.path.join(TESTDIR, 'valid_op_with_operation_resource.json')
        op_data = json.load(open(p))
        result = check_for_operation_resources(op_data)
        self.assertTrue(result.keys() == set(['pathway_file']))
        self.assertTrue(result.keys() != op_data['inputs'].keys())

        # check that no keys are returned
        p = os.path.join(TESTDIR, 'valid_operation.json')
        op_data = json.load(open(p))
        result = check_for_operation_resources(op_data)
        self.assertTrue(len(result.keys()) == 0)

    # the patched list here matches that of the file we use in this test:
    @mock.patch('api.utilities.ingest_operation.RESOURCE_TYPE_SET', 
        new=['I_MTX', 'EXP_MTX', 'OTHER'])
    def test_correctly_validates_operation_spec(self):
        '''
        While the structure of a data_structures.operation.Operation
        is checked/tested in the data_structures package, we intentionally
        avoid placing api-specific logic there.

        Hence, when an admin is attempting to add a new Operation, we need
        to validate parts of that data structure that depend on our API.
        An example is the resource type(s) for a particular operation
        input representing a file input. We need to check that the values
        they use are correct given the types of files we allow in the api
        '''
        fp = os.path.join(TESTDIR, 'valid_complete_workspace_operation.json')
        j = json.load(open(fp))
        op = Operation(j)
        validate_operation_spec(op)

    # the patched list here does NOT match that of the file we use in this test.
    # By removing 'EXP_MTX', we are testing that invalid resource types appearing
    # in the operation spec cause exceptions to be raised.
    @mock.patch('api.utilities.ingest_operation.RESOURCE_TYPE_SET', 
        new=['I_MTX', 'OTHER'])
    def test_correctly_fails_operation_spec(self):
        '''
        While the structure of a data_structures.operation.Operation
        is checked/tested in the data_structures package, we intentionally
        avoid placing api-specific logic there.

        Hence, when an admin is attempting to add a new Operation, we need
        to validate parts of that data structure that depend on our API.
        An example is the resource type(s) for a particular operation
        input representing a file input. We need to check that the values
        they use are correct given the types of files we allow in the api

        Here we fail due to an unknown/unexpected resource type in the spec
        file.
        '''
        fp = os.path.join(TESTDIR, 'valid_complete_workspace_operation.json')
        j = json.load(open(fp))
        op = Operation(j)
        with self.assertRaisesRegex(InvalidResourceTypeException, 'EXP_MTX'):
            validate_operation_spec(op)

    def test_correctly_fails_operation_spec_case2(self):
        fp = os.path.join(TESTDIR, 'valid_complete_workspace_operation.json')
        j = json.load(open(fp))
        j['mode'] = 'garbage'
        op = Operation(j)
        with self.assertRaisesRegex(InvalidRunModeException, 'garbage'):
            validate_operation_spec(op)  

    # @mock.patch('api.utilities.ingest_operation.get_resource_size')
    # @mock.patch('api.utilities.ingest_operation.move_resource_to_final_location')
    # @mock.patch('api.utilities.ingest_operation.get_storage_implementation')
    # def test_creation_of_operation_resource(self, 
    #     mock_get_storage_implementation,
    #     mock_move_resource_to_final_location,
    #     mock_get_resource_size):
    #     '''
    #     Tests the function that creates a new OperationResource.
    #     Mocks out most methods since they involve shuffling files 
    #     around, etc.-- merely tests that the expected calls are made

    #     Here, we mock it being a local file.
    #     '''
    #     mock_storage_impl = mock.MagicMock()
    #     mock_storage_impl.is_local_storage = True
    #     mock_get_storage_implementation.return_value = mock_storage_impl

    #     mock_final_path = '/some/final/path.tar'
    #     mock_move_resource_to_final_location.return_value = mock_final_path
    #     mock_get_resource_size.return_value = 100
    #     name = 'GRCh38 index'
    #     path = '/some/local/path.tar'
    #     op_resource_dict = {
    #         'name': name,
    #         'path': path,
    #         'resource_type': '*'
    #     }
    #     orig_op_resources = OperationResource.objects.all()
    #     ops = OperationDbModel.objects.all()
    #     if len(ops) == 0:
    #         raise ImproperlyConfigured('Need at least one Operation to work with.')
    #     else:
    #         op_uuid = ops[0].pk
    #     n0 = len(orig_op_resources)
    #     mock_staging_dir = '/some/staging/dir'
    #     result = create_operation_resource(
    #         'foo_input', 
    #         op_resource_dict, 
    #         op_uuid, 
    #         {}, 
    #         mock_staging_dir
    #     )
    #     expected_dict = {
    #         'name': name,
    #         'path': mock_final_path,
    #         'resource_type': '*'
    #     }
    #     self.assertDictEqual(result, expected_dict)
    #     final_op_resources = OperationResource.objects.all()
    #     n1 = len(final_op_resources)
    #     self.assertEqual(n1-n0, 1)
    #     mock_move_resource_to_final_location.assert_called()
    #     mock_get_resource_size.assert_called()
    #     expected_path = os.path.join(mock_staging_dir, path)
    #     mock_storage_impl.resource_exists.assert_called_with(expected_path)

    # @mock.patch('api.utilities.ingest_operation.get_resource_size')
    # @mock.patch('api.utilities.ingest_operation.move_resource_to_final_location')
    # @mock.patch('api.utilities.ingest_operation.get_storage_implementation')
    # def test_creation_of_operation_resource_case2(self, 
    #     mock_get_storage_implementation,
    #     mock_move_resource_to_final_location,
    #     mock_get_resource_size):
    #     '''
    #     Tests the function that creates a new OperationResource.
    #     Mocks out most methods since they involve shuffling files 
    #     around, etc.-- merely tests that the expected calls are made

    #     Here, we mock it being a non-local file.
    #     '''
    #     mock_storage_impl = mock.MagicMock()
    #     mock_storage_impl.is_local_storage = False
    #     mock_get_storage_implementation.return_value = mock_storage_impl

    #     mock_final_path = '/some/final/path.tar'
    #     mock_move_resource_to_final_location.return_value = mock_final_path
    #     mock_get_resource_size.return_value = 100
    #     name = 'GRCh38 index'
    #     path = '/some/local/path.tar'
    #     op_resource_dict = {
    #         'name': name,
    #         'path': path,
    #         'resource_type': '*'
    #     }
    #     orig_op_resources = OperationResource.objects.all()
    #     ops = OperationDbModel.objects.all()
    #     if len(ops) == 0:
    #         raise ImproperlyConfigured('Need at least one Operation to work with.')
    #     else:
    #         op_uuid = ops[0].pk
    #     n0 = len(orig_op_resources)
    #     mock_staging_dir = '/some/staging/dir'
    #     result = create_operation_resource(
    #         'foo_input', 
    #         op_resource_dict, 
    #         op_uuid, 
    #         {}, 
    #         mock_staging_dir
    #     )
    #     expected_dict = {
    #         'name': name,
    #         'path': mock_final_path,
    #         'resource_type': '*'
    #     }
    #     self.assertDictEqual(result, expected_dict)
    #     final_op_resources = OperationResource.objects.all()
    #     n1 = len(final_op_resources)
    #     self.assertEqual(n1-n0, 1)
    #     mock_move_resource_to_final_location.assert_called()
    #     mock_get_resource_size.assert_called()
    #     mock_storage_impl.resource_exists.assert_called_with(path)