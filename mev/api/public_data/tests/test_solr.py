import unittest
import unittest.mock as mock
import json
import uuid
import os
import datetime

from django.conf import settings

from api.public_data.indexers.solr import SolrIndexer

THIS_DIR = os.path.dirname(os.path.abspath(__file__))

class TestSolrIndexer(unittest.TestCase): 

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

    

    @mock.patch('api.public_data.indexers.solr.run_shell_command')
    @mock.patch('api.public_data.indexers.solr.os.path.dirname')
    @mock.patch('api.public_data.indexers.solr.os.path.abspath')
    @mock.patch('api.public_data.indexers.solr.os.path.exists')
    def test_core_creation_called_correctly(self, 
        mock_exists, 
        mock_abspath,
        mock_dirname,
        mock_run_shell_command):
        '''
        Check that we make the proper call to create a core
        '''
        mock_dir = 'some/dir'
        mock_dirname.return_value = mock_dir
        mock_abspath.return_value = ''
        mock_exists.return_value = True
        index_name = 'foo-{s}'.format(s=str(uuid.uuid4()))
        mock_schema_dir = os.path.join(mock_dir, 'solr', index_name)
        expected_command = '{solr} create_core -c {idx} -d {dir}'.format(
            idx = index_name,
            solr = self.indexer.SOLR_CMD,
            dir = mock_schema_dir
        )
        mock_run_shell_command.return_value = ('','')
        self.indexer._create_core(index_name)
        mock_run_shell_command.assert_called_with(expected_command)