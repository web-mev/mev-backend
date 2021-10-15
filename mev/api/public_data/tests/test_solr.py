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
        ann_filepath = os.path.join(THIS_DIR, 'test_files', 'test_annotation_data.csv')
        mock_core_name = 'foo'

        class MockResponse(object):
            def __init__(self):
                self.status_code = 200
            def json(self):
                return 'something'

        mock_response_obj = MockResponse()
        print('mock_resp_obj: ', mock_response_obj)
        mock_post.return_value = mock_response_obj
        self.indexer.index(mock_core_name, ann_filepath)
        expected_url ='{host}/{core}/update/'.format(
            host=self.indexer.SOLR_SERVER, core=mock_core_name)
        mock_post.assert_called_with(expected_url,
            data=open(ann_filepath, 'r').read(),
            params={'commit': 'true'},
            headers={'content-type': mock_content_type}
        )

