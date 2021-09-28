import os
import requests
import json
import logging

from api.utilities.basic_utils import run_shell_command
from api.public_data.indexers.base import BaseIndexer

logger = logging.getLogger(__name__)


class SolrIndexer(BaseIndexer):
    """
    This class implements our interface to the solr service
    """
    # TODO: extract this to settings or otherwise
    SOLR_BIN_DIR = '/opt/solr/bin'

    SOLR_POST_CMD = '{bin_dir}/post'.format(bin_dir=SOLR_BIN_DIR)
    SOLR_CMD = '{bin_dir}/solr'.format(bin_dir=SOLR_BIN_DIR)

    # TODO: extract this to settings or otherwise
    SOLR_SERVER = 'http://localhost:8983/solr'

    # relative to the SOLR_SERVER url
    CORES_URL = 'solr/admin/cores'

    def index(self, index_name, path):
        '''
        Given a local path, index the data in that file.
        '''
        
        # Check if the core exists. If not, we have to create it
        if not self._check_if_core_exists(index_name):
            self._create_core(index_name)

        # index the file:
        cmd = '{post_cmd} -c {index_name} {path}'.format(
            post_cmd = self.SOLR_POST_CMD,
            index_name = index_name,
            path = path
        )
        try:
            stdout, stderr = run_shell_command(cmd)
        except Exception as ex:
            logger.info('Failed to index the file at {p}'
                ' in the collection {idx}.'.format(
                    p = path,
                    idx = index_name
                )
            )
            raise ex

    def query(self, index_name, query_string):
        '''
        Perform and return the query response from solr.
        `index_name` identifies the solr collection/core we are querying
        `query_string` is the query string appended to the url.
        '''
        query_url = '{base_url}/{index_name}/select?{query_str}'.format(
            base_url = self.SOLR_SERVER,
            index_name = index_name,
            query_str = query_string
        ) 
        r = requests.get(query_url)
        if r.status_code == 200:
            try:
                j = r.json()
            except json.decoder.JSONDecodeError:
                logger.error('The response had status 200, but'
                    ' could not be parsed as JSON.'
                )
                raise Exception('Unexpected response from solr server.'
                    ' The query was successful, but could not interpret'
                    ' the response as JSON.'
                )
            return self._reformat_response(j) 
        else:
            payload = r.json()
            error_msg = payload['error']['msg']
            logger.info('The query to {u} failed. Message was: {m}'.format(
                u=query_url,
                m = error_msg
            ))
            raise Exception('Query failed. Error message was: {m}'.format(
                m = error_msg
            ))

    def _reformat_response(self, solr_response):
        '''
        This method reformats the response provided by solr. Depending on how
        the query was presented, we want to return different formats to the front
        end. 
        '''
        return solr_response

    def _check_if_core_exists(self, index_name):
        '''
        Return a boolean indicating whether there is already
        a core with the given name
        '''
        # A reliable way to check if a core exists is to attempt a query on it.
        # If the core does NOT exist, should get a 404 response

        # Here, make a wildcard query for a single record. 
        url = '{base_url}/{index_name}/select?{query_str}'.format(
            base_url = self.SOLR_SERVER,
            index_name = index_name,
            query_str = 'q=*:*&rows=1'
        ) 
        r = requests.get(url)
        if r.status_code == 200:
            return True
        return False


    def _create_core(self, index_name):
        '''
        Creates a new core with the given index name
        '''

        # We expect that there should be a directory containing files for the index
        # at the proper location. If that directory doesn't exist, fail out.
        this_dir = os.path.dirname(os.path.abspath(__file__))
        schema_dir = os.path.join(this_dir, 'solr', index_name)
        if not os.path.exists(schema_dir):
            raise Exception('The expected solr index directory did not exist.'
                ' Please check that the proper schema files exist at {d}'.format(
                    d = schema_dir
                )
            )

        cmd = '{solr_cmd} create_core -c {index_name} -d {schema_dir}'.format(
            solr_cmd = self.SOLR_CMD,
            index_name = index_name,
            schema_dir = schema_dir
        )
        try:
            stdout, stderr = run_shell_command(cmd)
            logger.info('Completed creating core. Stdout={stdout}'.format(
                stdout=stdout
            ))
        except Exception as ex:
            logger.info('Failed to create a solr core with'
                ' name {idx}.'.format(
                    idx = index_name
                )
            )
            raise ex

    def _delete_core(self, index_name):
        '''
        Deletes a core with the given index name
        '''
        cmd = '{solr_cmd} delete -c {index_name}'.format(
            solr_cmd = self.SOLR_CMD,
            index_name = index_name,
        )
        try:
            stdout, stderr = run_shell_command(cmd)
            logger.info('Completed deleting core. Stdout={stdout}'.format(
                stdout=stdout
            ))
        except Exception as ex:
            logger.info('Failed to delete a solr core with'
                ' name {idx}.'.format(
                    idx = index_name
                )
            )
            raise ex
