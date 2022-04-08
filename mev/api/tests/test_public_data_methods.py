import json
import shutil
import unittest
import unittest.mock as mock
import os
import datetime
import pandas as pd
import uuid

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from api.tests.base import BaseAPITestCase


from api.public_data import DATASETS, \
    index_dataset, \
    create_dataset_from_params
from api.models import PublicDataset
from api.public_data.sources.base import PublicDataSource
from api.public_data.sources.gdc.gdc import GDCDataSource, \
    GDCRnaSeqDataSourceMixin
from api.public_data.sources.rnaseq import RnaSeqMixin
from api.public_data.sources.gdc.tcga import TCGADataSource
from api.public_data.sources.gdc.target import TargetDataSource
from api.public_data.sources.gtex_rnaseq import GtexRnaseqDataSource
from api.public_data.indexers.solr import SolrIndexer


THIS_DIR = os.path.dirname(os.path.abspath(__file__))

class TestSolrIndexer(BaseAPITestCase): 

    def setUp(self):
        '''
        Note that this setup method is implicitly testing the 
        the core creation and indexing methods
        '''
        self.indexer = SolrIndexer()

    @mock.patch('api.public_data.indexers.solr.requests')
    def test_query_call(self, mock_requests):
        '''
        Test the method where we check make a query request
        '''
        query_str = 'facet.field=project_id&q=*:*&rows=2&'
        index_name = 'foo-{s}'.format(s=str(uuid.uuid4()))
        expected_url = '{solr_server}/{idx}/select?{q}'.format(
            q = query_str,
            idx = index_name, 
            solr_server = self.indexer.SOLR_SERVER
        )
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        d1 = {'a':1, 'b':2}
        mock_response.json.return_value = d1
        mock_requests.get.return_value = mock_response
        mock_reformat_method = mock.MagicMock()
        d2 = {'c':3, 'd':4}
        mock_reformat_method.return_value = d2
        self.indexer._reformat_response = mock_reformat_method
        result = self.indexer.query(index_name, query_str)
        self.assertDictEqual(result, d2)
        mock_requests.get.assert_called_with(expected_url)
        mock_reformat_method.assert_called_with(d1)

    @mock.patch('api.public_data.indexers.solr.requests')
    def test_bad_query_call(self, mock_requests):
        '''
        Test the method where we check make a query request
        but a bad query is supplied. Solr would issue some kind
        of error message which we mock here.
        '''

        query_str = 'foo=bar'
        index_name = 'foo-{s}'.format(s=str(uuid.uuid4()))
        expected_url = '{solr_server}/{idx}/select?{q}'.format(
            q = query_str,
            idx = index_name, 
            solr_server = self.indexer.SOLR_SERVER
        )
        mock_response = mock.MagicMock()
        mock_response.status_code = 400
        d1 = {'error':{'xyz':1, 'msg':'Something bad happened!'}}
        mock_response.json.return_value = d1
        mock_requests.get.return_value = mock_response

        with self.assertRaises(Exception):
            self.indexer.query(index_name, query_str)
        mock_requests.get.assert_called_with(expected_url)


    @mock.patch('api.public_data.indexers.solr.requests')
    def test_core_check_works(self, mock_requests):
        '''
        Test the method where we check if a core exists.
        Here, we mock out the actual request to the solr
        server.    
        '''
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_requests.get.return_value = mock_response

        self.assertTrue(self.indexer._check_if_core_exists('some name'))

        mock_response.status_code = 400
        mock_requests.get.return_value = mock_response
        self.assertFalse(self.indexer._check_if_core_exists('junk'))

        mock_response.status_code = 404
        mock_requests.get.return_value = mock_response
        self.assertFalse(self.indexer._check_if_core_exists('junk'))

    @mock.patch('api.public_data.indexers.solr.requests.post')
    @mock.patch('api.public_data.indexers.solr.SolrIndexer._check_if_core_exists')
    @mock.patch('api.public_data.indexers.solr.mimetypes')
    def test_index_call_correctly_made(self, mock_mimetypes,
        mock_check_core, 
        mock_post):
        '''
        Tests that we are issuing the proper request to index a file with solr
        '''
        mock_check_core.return_value = True
        mock_content_type = 'text/csv'
        mock_mimetypes.guess_type.return_value = (mock_content_type,None)
        ann_filepath = os.path.join(THIS_DIR, 'public_data_test_files', 'test_annotation_data.csv')
        mock_core_name = 'foo'

        class MockResponse(object):
            def __init__(self):
                self.status_code = 200
            def json(self):
                return 'something'

        mock_response_obj = MockResponse()
        mock_post.return_value = mock_response_obj
        self.indexer.index(mock_core_name, ann_filepath)
        expected_url ='{host}/{core}/update/'.format(
            host=self.indexer.SOLR_SERVER, core=mock_core_name)
        mock_post.assert_called_with(expected_url,
            data=open(ann_filepath, 'r').read(),
            params={'commit': 'true'},
            headers={'content-type': mock_content_type}
        )


class TestPublicDatasets(BaseAPITestCase): 

    fixtures = [settings.TESTING_DB_DUMP]

    def setUp(self):
        self.all_public_datasets = PublicDataset.objects.filter(active=True)

        if len(self.all_public_datasets) == 0:
            raise ImproperlyConfigured('Need at least one active public dataset to'
                ' run this test properly.'
            )

        # grab the first dataset to use in the tests below
        self.test_dataset = self.all_public_datasets[0]

    def test_unique_tags(self):
        '''
        This test serves as a check that we did not accidentally duplicate
        a tag (the `TAG` attribute on the implementing public dataset classes)
        '''
        unique_tags = set(DATASETS)
        self.assertTrue(len(unique_tags) == len(DATASETS))

    @mock.patch('api.public_data.get_indexer')
    @mock.patch('api.public_data.get_implementing_class')
    def test_indexing_steps(self, mock_get_implementing_class, mock_get_indexer):
        '''
        This test verifies that the proper methods are called 
        and that the database is updated accordingly
        '''
        index_name = self.test_dataset.index_name

        mock_dataset = mock.MagicMock()
        mock_dataset.PUBLIC_NAME = 'foo'
        mock_dataset.DESCRIPTION = 'desc'
        mock_dataset.get_indexable_files.return_value = ['a','b']
        mock_dataset.get_additional_metadata.return_value = {'something': 100}
        mock_indexer = mock.MagicMock()

        mock_get_implementing_class.return_value = mock_dataset
        mock_get_indexer.return_value = mock_indexer

        file_mapping = {
            'abc': [1,2,3]
        }

        # make the call to the function
        index_dataset(self.test_dataset, file_mapping)

        # verify that the 
        mock_dataset.verify_files.assert_called_with(file_mapping)
        mock_dataset.get_indexable_files.assert_called_with(file_mapping)
        mock_indexer.index.assert_has_calls([
            mock.call(index_name, 'a'),
            mock.call(index_name, 'b')
        ])

        # query the database to check that it was updated
        p = PublicDataset.objects.get(pk=self.test_dataset.pk)
        self.assertDictEqual(p.file_mapping, file_mapping)
        self.assertEqual('foo', p.public_name)
        self.assertEqual('desc', p.description)

    @mock.patch('api.public_data.validate_resource_and_store')
    @mock.patch('api.public_data.get_implementing_class')
    @mock.patch('api.public_data.check_if_valid_public_dataset_name')
    @mock.patch('api.public_data.Resource')
    def test_dataset_creation_steps_case1(self, mock_resource_class,
            mock_check_if_valid_public_dataset_name, 
            mock_get_implementing_class,
            mock_validate_and_store_resource
        ):
        '''
        Tests the proper methods are called for the process of creating a 
        public dataset for a user. Here, we do not pass an output name
        to the method. The output_name allows a user to give a custom name
        to the exported files. Otherwise they are auto-named
        '''

        dataset_id = self.test_dataset.index_name
        mock_user = mock.MagicMock()
        mock_dataset = mock.MagicMock()
        mock_resource_instance = mock.MagicMock()
        mock_name = 'filename.tsv'
        mock_resource_instance.name = mock_name
        pk=1111
        mock_resource_instance.pk = pk
        filetype = 'MTX'

        mock_dataset.create_from_query.return_value = (['a'], [mock_name], [filetype])

        mock_resource_class.objects.create.return_value =  mock_resource_instance
        validate_str = 'validating...'
        mock_resource_class.VALIDATING = validate_str

        mock_check_if_valid_public_dataset_name.return_value = True
        mock_get_implementing_class.return_value = mock_dataset

        mock_final_path = '/a/b/c.txt'

        # doesn't matter what this actually is since
        # it depends on the actual dataset being implemented.
        request_payload = {
            'filters': []
        }

        resource_list = create_dataset_from_params(dataset_id, mock_user, request_payload)

        # check the proper methods were called:
        mock_dataset.create_from_query.assert_called_with(self.test_dataset, request_payload, '')
        mock_validate_and_store_resource.delay.assert_called_with(mock_resource_instance.pk, filetype)
        mock_resource_class.objects.create.assert_called_with(
            name = mock_name,
            owner=mock_user,
            path='a',
            status = validate_str
        )

        self.assertEqual(resource_list[0].name, mock_name)

    @mock.patch('api.public_data.validate_resource_and_store')
    @mock.patch('api.public_data.get_implementing_class')
    @mock.patch('api.public_data.check_if_valid_public_dataset_name')
    @mock.patch('api.public_data.Resource')
    def test_dataset_creation_fails(self, mock_resource_class,
            mock_check_if_valid_public_dataset_name, 
            mock_get_implementing_class,
            mock_validate_and_store_resource
        ):
        '''
        Tests that we do not create a Resource in the case where the
        `create_from_query` method fails for some reason
        '''

        dataset_id = self.test_dataset.index_name
        mock_user = mock.MagicMock()
        mock_dataset = mock.MagicMock()

        mock_dataset.create_from_query.side_effect= Exception('something bad!')

        mock_check_if_valid_public_dataset_name.return_value = True
        mock_get_implementing_class.return_value = mock_dataset

        # doesn't matter what this actually is since
        # it depends on the actual dataset being implemented.
        request_payload = {
            'filters': []
        }

        with self.assertRaises(Exception):
            create_dataset_from_params(dataset_id, mock_user, request_payload)

        # check that methods were NOT called:
        mock_resource_class.objects.create.assert_not_called()
        mock_validate_and_store_resource.delay.assert_not_called()


class TestBasePublicDataSource(BaseAPITestCase):

    @mock.patch('api.public_data.sources.base.os')
    def test_check_file_dict(self, mock_os):
        '''
        Tests a method in the base class that asserts the proper
        files were passed during indexing
        '''

        mock_os.path.exists.return_value = True

        pds = PublicDataSource()

        # below, we pass a dict which identifies files passed to the 
        # class. This, for instance, allows us to know which file is the 
        # annotation file(s) and which is the count matrix. Each class
        # implementation has some necessary files and they will define this:
        pds.DATASET_FILES = ['keyA', 'keyB']

        # a valid dict
        fd = {
            'keyA': ['/path/to/fileA.txt'],
            'keyB': ['/path/to/fileB.txt', '/path/to/another_file.txt']
        }
        pds.check_file_dict(fd)

        # has an extra key- ok to ignore
        fd = {
            'keyA': ['/path/to/fileA.txt'],
            'keyB': ['/path/to/fileB.txt', '/path/to/another_file.txt'],
            'keyC': ['']
        }
        pds.check_file_dict(fd)

        # uses the wrong keys- keyA is missing
        fd = {
            'keyC': ['/path/to/fileA.txt'],
            'keyB': ['/path/to/fileB.txt', '/path/to/another_file.txt']
        }
        with self.assertRaisesRegex(Exception, 'keyA'):
            pds.check_file_dict(fd)

        # Each key should address a list
        fd = {
            'keyA': '/path/to/fileA.txt',
            'keyB': ['/path/to/fileB.txt', '/path/to/another_file.txt']
        }
        with self.assertRaisesRegex(Exception, 'keyA'):
            pds.check_file_dict(fd)

        # mock non-existent filepath
        mock_os.path.exists.side_effect = [True, False, True]
        fd = {
            'keyA': ['/path/to/fileA.txt'],
            'keyB': ['/path/to/fileB.txt', '/path/to/another_file.txt']
        }
        with self.assertRaisesRegex(Exception, '/path/to/fileB.txt'):
            pds.check_file_dict(fd)     

        

class TestGDC(BaseAPITestCase): 
    def test_dummy(self):
        self.assertTrue(True)


class TestTCGA(BaseAPITestCase): 
    def test_gets_all_tcga_types(self):
        '''
        Tests that we get the response from querying all the TCGA types
        from the GDC API. While we don't check the full set, we confirm
        that a few known types are there as a sanity check.
        '''
        ds = TCGADataSource()
        tcga_cancer_types = ds.query_for_project_names_within_program('TCGA')
        self.assertTrue('TCGA-BRCA' in tcga_cancer_types.keys())

        self.assertTrue(tcga_cancer_types['TCGA-LUAD'] == 'Lung Adenocarcinoma')

class TestTARGET(BaseAPITestCase): 
    def test_gets_all_target_types(self):
        '''
        Tests that we get the response from querying all the TARGET types
        from the GDC API. While we don't check the full set, we confirm
        that a few known types are there as a sanity check.
        '''
        ds = TargetDataSource()
        target_types = ds.query_for_project_names_within_program('TARGET')
        self.assertTrue('TARGET-NBL' in target_types.keys())

        self.assertTrue(target_types['TARGET-NBL'] == 'Neuroblastoma')

class TestGDCRnaSeqMixin(BaseAPITestCase): 

    def test_proper_filters_created(self):
        '''
        Tests that the json payload for a metadata
        query is created as expected
        '''
        ds = GDCRnaSeqDataSourceMixin()
        d = ds._create_rnaseq_query_params('TCGA-FOO')

        # Note that in the dict below, the value of the 'filters' key is itself a JSON
        # format string. The GDC API will not accept if that value happened to be a native
        # python dict
        expected_query_filters = {
            "fields": "file_id,file_name,cases.project.program.name,cases.case_id,cases.aliquot_ids,cases.samples.portions.analytes.aliquots.aliquot_id",
            "format": "JSON",
            "size": "100",
            "expand": "cases.demographic,cases.diagnoses,cases.exposures,cases.tissue_source_site,cases.project",
            "filters": "{\"op\": \"and\", \"content\": [{\"op\": \"in\", \"content\": {\"field\": \"files.cases.project.project_id\", \"value\": [\"TCGA-FOO\"]}}, {\"op\": \"in\", \"content\": {\"field\": \"files.analysis.workflow_type\", \"value\": [\"HTSeq - Counts\"]}}, {\"op\": \"in\", \"content\": {\"field\": \"files.experimental_strategy\", \"value\": [\"RNA-Seq\"]}}, {\"op\": \"in\", \"content\": {\"field\": \"files.data_type\", \"value\": [\"Gene Expression Quantification\"]}}]}"
        }
        self.assertDictEqual(d, expected_query_filters)      

    @mock.patch('api.public_data.sources.rnaseq.RnaSeqMixin.COUNT_OUTPUT_FILE_TEMPLATE', '__TEST__counts.{tag}.{ds}.tsv')
    def test_counts_merged_correctly(self):
        file_to_aliquot_mapping = {
            's1': 'x1',
            's2': 'x2',
            's3': 'x3'
        }
        expected_matrix = pd.DataFrame(
            [[509, 1446, 2023],[0,2,22],[1768, 2356, 1768]],
            index=['ENSG00000000003','ENSG00000000005','ENSG00000000419'],
            columns = ['x1', 'x2', 'x3']
        )
        expected_matrix.index.name = 'gene'

        archives = [
            os.path.join(THIS_DIR, 'public_data_test_files', 'archive1.tar.gz'),
            os.path.join(THIS_DIR, 'public_data_test_files', 'archive2.tar.gz')
        ]

        data_src = GDCRnaSeqDataSourceMixin()
        # The derived classes will have a ROOT_DIR attribute, but
        # this mixin class doesn't. Patch it here
        data_src.ROOT_DIR = '/tmp'
        actual_df = data_src._merge_downloaded_archives(archives, file_to_aliquot_mapping)
        self.assertTrue(expected_matrix.equals(actual_df))

class TestGTExRnaseq(BaseAPITestCase):

    @mock.patch('api.public_data.sources.gtex_rnaseq.GtexRnaseqDataSource._get_sample_annotations')
    @mock.patch('api.public_data.sources.gtex_rnaseq.GtexRnaseqDataSource._get_phenotype_data')
    @mock.patch('api.public_data.sources.gtex_rnaseq.GtexRnaseqDataSource._download_file')
    @mock.patch('api.public_data.sources.gtex_rnaseq.GtexRnaseqDataSource._create_tmp_dir')
    @mock.patch('api.public_data.sources.gtex_rnaseq.run_shell_command')
    def test_data_prep(self, \
        mock_run_shell_command, \
        mock_create_tmp_dir, \
        mock_download_file, \
        mock_get_phenotype_data, \
        mock_get_sample_annotations):
        '''
        Test that we munge everything correctly
        '''
        mock_tmp_dir = os.path.join(
            THIS_DIR, 
            'public_data_test_files'
        )
        mock_create_tmp_dir.return_value = mock_tmp_dir
        ann_path = os.path.join(
            THIS_DIR, 
            'public_data_test_files', 
            'gtex_rnaseq_ann.tsv'
        )
        pheno_path = os.path.join(
            THIS_DIR, 
            'public_data_test_files', 
            'gtex_rnaseq_pheno.tsv'
        )

        mock_get_sample_annotations.return_value = pd.read_table(ann_path)
        mock_get_phenotype_data.return_value = pd.read_table(pheno_path)

        tmp_testing_dir = os.path.join(settings.DATA_DIR, 'test-gtex-rnaseq')
        os.mkdir(tmp_testing_dir)
        GtexRnaseqDataSource.ROOT_DIR = tmp_testing_dir 
        mock_adipose_url = 'adipose_url'
        mock_blood_url = 'blood_url'
        GtexRnaseqDataSource.TISSUE_TO_FILE_MAP = {
            'Adipose - Subcutaneous': mock_adipose_url,
            'Whole Blood': mock_blood_url
        }
        data_src = GtexRnaseqDataSource()
        data_src.prepare()
        f = RnaSeqMixin.COUNT_OUTPUT_FILE_TEMPLATE.format(
            tag = data_src.TAG,
            date = data_src.date_str
        )
        ann_output = RnaSeqMixin.ANNOTATION_OUTPUT_FILE_TEMPLATE.format(
            tag = data_src.TAG,
            date = data_src.date_str
        )
        expected_output_hdf = os.path.join(tmp_testing_dir, f)
        expected_output_ann = os.path.join(tmp_testing_dir, ann_output)
        self.assertTrue(os.path.exists(expected_output_hdf))
        self.assertTrue(os.path.exists(expected_output_ann))

        expected_tissue_list = [
            'Adipose - Subcutaneous', 
            'Whole Blood'
        ]
        converted_tissue_list = [RnaSeqMixin.create_python_compatible_id(x) for x in expected_tissue_list]
        groups_list = ['/{x}/ds'.format(x=x) for x in converted_tissue_list]
        with pd.HDFStore(expected_output_hdf) as hdf:
            self.assertCountEqual(groups_list, list(hdf.keys()))

        # cleanup the test folder
        shutil.rmtree(tmp_testing_dir)

        shell_calls = []
        for i in range(2):
            f = os.path.join(mock_tmp_dir, 'f{x}.gct.gz'.format(x=i))
            shell_calls.append(mock.call('gunzip {f}'.format(f=f)))
        mock_run_shell_command.assert_has_calls(shell_calls)
        mock_download_file.assert_has_calls([
            mock.call(
                mock_adipose_url, os.path.join(mock_tmp_dir, 'f0.gct.gz')
            ),
            mock.call(
                mock_blood_url, os.path.join(mock_tmp_dir, 'f1.gct.gz'))
        ])


class TestRnaSeqMixin(BaseAPITestCase): 

    def test_indexes_only_annotation_file(self):
        '''
        An RNA-seq dataset consists of a metadata file and a count matrix.
        This verifies that the `get_indexable_files`  method only returns
        the annotation file
        '''

        data_src = RnaSeqMixin()

        fd = {
            RnaSeqMixin.ANNOTATION_FILE_KEY: ['/path/to/A.txt'],
            RnaSeqMixin.COUNTS_FILE_KEY:['/path/to/counts.tsv'] 
        }
        result = data_src.get_indexable_files(fd)
        self.assertCountEqual(result, fd[RnaSeqMixin.ANNOTATION_FILE_KEY])

    @mock.patch('api.public_data.sources.rnaseq.uuid')
    def test_filters_hdf_correctly(self, mock_uuid_mod):
        '''
        Tests that we filter properly for a 
        dummy dataset stored in HDF5 format.
        '''
        hdf_path = os.path.join(
            THIS_DIR, 
            'public_data_test_files', 
            'tcga_rnaseq.hd5'
        )

        ann_path = os.path.join(
            THIS_DIR, 
            'public_data_test_files', 
            'tcga_rnaseq_ann.csv'
        )

        # create 5 mock UUIDs. The first two are used in the 
        # first call to the tested method. The final 3 are used in the second
        # call to the tested method. The reason for that is we auto-generate
        # the output filename when the calling function has not provided an 
        # `output_name` arg to the method. In the first call to the tested
        # method, we provide that name, so only two calls are made to the 
        # uuid.uuid4 function. In the second call, we omit that arg and we 
        # hence make an extra call to the uuid4 func.
        mock_uuids = [uuid.uuid4() for i in range(5)]
        mock_uuid_mod.uuid4.side_effect = mock_uuids

        # this dict is what the database record is expected to contain
        # in the file_mapping field
        mock_mapping = {
            # this key doesn't matter- we just include it as a correct
            RnaSeqMixin.ANNOTATION_FILE_KEY: [ann_path],
            RnaSeqMixin.COUNTS_FILE_KEY:[hdf_path] 

        }
        mock_db_record = mock.MagicMock()
        mock_db_record.file_mapping = mock_mapping
        query = {
            'TCGA-ABC': ['s1', 's3'],
            'TCGA-DEF': ['s5']
        }
        data_src = RnaSeqMixin()
        # the children classes will have a TAG attribute. Since we are
        # testing this mixin here, we simply patch it
        tag = 'foo'
        data_src.TAG = tag
        output_name = 'abc'
        paths, filenames, resource_types = data_src.create_from_query(mock_db_record, query, output_name)

        # The order of these doesn't matter in practice, but to check the file contents,
        # we need to be sure we're looking at the correct files for this test.
        self.assertTrue(resource_types[0] == 'RNASEQ_COUNT_MTX')
        self.assertTrue(resource_types[1] == 'ANN')
        expected_df = pd.DataFrame(
            [[26,86,67],[54,59,29],[24,12,37]],
            index = ['gA', 'gB', 'gC'],
            columns = ['s1','s3','s5']
        )
        actual_df = pd.read_table(paths[0], index_col=0)
        self.assertTrue(actual_df.equals(expected_df))

        ann_df = pd.DataFrame(
            [['TCGA-ABC', 1990],['TCGA-ABC', 1992], ['TCGA-DEF', 1994]],
            index = ['s1','s3','s5'],
            columns = ['cancer_type', 'year_of_birth']
        )
        actual_df = pd.read_table(paths[1], index_col=0)
        self.assertTrue(actual_df.equals(ann_df))

        self.assertEqual(filenames[0], '{x}_counts.{t}.tsv'.format(x=output_name, t=tag))
        self.assertEqual(filenames[1], '{x}_ann.{t}.tsv'.format(x=output_name, t=tag))

        # use index 4 below as 2 uuid.uuid4 calls were 'consumed' by the first call to `create_From_query`
        # while the second call  (the one we are testing now) uses 3 calls to
        paths, filenames, resource_types = data_src.create_from_query(mock_db_record, query)
        self.assertEqual(filenames[0], '{t}_counts.{u}.tsv'.format(u=mock_uuids[4], t=tag))
        self.assertEqual(filenames[1], '{t}_ann.{u}.tsv'.format(u=mock_uuids[4], t=tag))

    def test_rejects_whole_dataset_with_null_filter(self):
        '''
        Tests that we reject the request (raise an exception)
        if a filter of None is applied. This would be too large 
        for us to handle.
        '''
        hdf_path = os.path.join(
            THIS_DIR, 
            'public_data_test_files', 
            'tcga_rnaseq.hd5'
        )

        # this dict is what the database record is expected to contain
        # in the file_mapping field
        mock_mapping = {
            # this key doesn't matter- we just include it as a correct
            # representation of the database record
            RnaSeqMixin.ANNOTATION_FILE_KEY: ['/dummy.tsv'],
            RnaSeqMixin.COUNTS_FILE_KEY:[hdf_path] 

        }
        mock_db_record = mock.MagicMock()
        mock_db_record.file_mapping = mock_mapping
        data_src = RnaSeqMixin()
        data_src.PUBLIC_NAME = 'foo' # the actual implementing class would define this attr typically
        with self.assertRaisesRegex(Exception, 'too large'):
            path, resource_type = data_src.create_from_query(mock_db_record, None)

    def test_filters_with_cancer_type(self):
        '''
        Tests that we handle a bad group ID appropriately
        '''
        hdf_path = os.path.join(
            THIS_DIR, 
            'public_data_test_files', 
            'tcga_rnaseq.hd5'
        )

        # this dict is what the database record is expected to contain
        # in the file_mapping field
        mock_mapping = {
            # this key doesn't matter- we just include it as a correct
            # representation of the database record
            RnaSeqMixin.ANNOTATION_FILE_KEY: ['/dummy.tsv'],
            RnaSeqMixin.COUNTS_FILE_KEY:[hdf_path] 

        }
        mock_db_record = mock.MagicMock()
        mock_db_record.file_mapping = mock_mapping
        query = {
            # the only datasets in the hdf5 file are for TCGA-ABC
            # and TCGA-DEF. Below, we ask for a non-existant one
            'TCGA-ABC': ['s1', 's3'],
            'TCGA-XYZ': ['s5']
        }
        data_src = RnaSeqMixin()
        with self.assertRaisesRegex(Exception, 'TCGA-XYZ'):
            paths, resource_types = data_src.create_from_query(mock_db_record, query)

    def test_filters_with_bad_sample_id(self):
        '''
        Tests that we handle missing samples appropriately
        '''
        hdf_path = os.path.join(
            THIS_DIR, 
            'public_data_test_files', 
            'tcga_rnaseq.hd5'
        )

        # this dict is what the database record is expected to contain
        # in the file_mapping field
        mock_mapping = {
            # this key doesn't matter- we just include it as a correct
            # representation of the database record
            RnaSeqMixin.ANNOTATION_FILE_KEY: ['/dummy.tsv'],
            RnaSeqMixin.COUNTS_FILE_KEY:[hdf_path] 

        }
        mock_db_record = mock.MagicMock()
        mock_db_record.file_mapping = mock_mapping
        query = {
            # add a bad sample ID to the TCGA-ABC set:
            'TCGA-ABC': ['s1111', 's3'],
            'TCGA-DEF': ['s5']
        }
        data_src = RnaSeqMixin()
        with self.assertRaisesRegex(Exception, 's1111'):
            paths, resource_types = data_src.create_from_query(mock_db_record, query)

    def test_empty_filters(self):
        '''
        Tests that we reject if the filtering list is empty
        '''
        hdf_path = os.path.join(
            THIS_DIR, 
            'public_data_test_files', 
            'tcga_rnaseq.hd5'
        )

        # this dict is what the database record is expected to contain
        # in the file_mapping field
        mock_mapping = {
            # this key doesn't matter- we just include it as a correct
            # representation of the database record
            RnaSeqMixin.ANNOTATION_FILE_KEY: ['/dummy.tsv'],
            RnaSeqMixin.COUNTS_FILE_KEY:[hdf_path] 

        }
        mock_db_record = mock.MagicMock()
        mock_db_record.file_mapping = mock_mapping
        query = {
            # This should have some strings:
            'TCGA-DEF': []
        }
        data_src = RnaSeqMixin()
        with self.assertRaisesRegex(Exception, 'empty'):
            paths, names, resource_types = data_src.create_from_query(mock_db_record, query)
            #paths, names, resource_types = data_src.create_from_query(query)

    def test_malformatted_filter_dict(self):
        '''
        Tests that we reject if the cancer type refers to something
        that is NOT a list
        '''
        hdf_path = os.path.join(
            THIS_DIR, 
            'public_data_test_files', 
            'tcga_rnaseq.hd5'
        )

        # this dict is what the database record is expected to contain
        # in the file_mapping field
        mock_mapping = {
            # this key doesn't matter- we just include it as a correct
            # representation of the database record
            RnaSeqMixin.ANNOTATION_FILE_KEY: ['/dummy.tsv'],
            RnaSeqMixin.COUNTS_FILE_KEY:[hdf_path] 

        }
        mock_db_record = mock.MagicMock()
        mock_db_record.file_mapping = mock_mapping
        query = {
            # This should be a list:
            'TCGA-DEF':'abc'
        }
        data_src = RnaSeqMixin()
        # again, the children will provide an EXAMPLE_PAYLOAD attribute
        # which we patch into this mixin class here
        data_src.EXAMPLE_PAYLOAD = {
        'TCGA-UVM': ["<UUID>","<UUID>"],
        'TCGA-MESO': ["<UUID>","<UUID>", "<UUID>"]
        }
        with self.assertRaisesRegex(Exception, 'a list of sample identifiers'):
            paths, resource_types = data_src.create_from_query(mock_db_record, query)
