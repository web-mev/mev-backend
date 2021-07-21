import os
import requests
import logging

from api.utilities.basic_utils import run_shell_command
from api.public_data.indexers.base import BaseIndexer

logger = logging.getLogger(__name__)

class SolrIndexer(BaseIndexer):
    '''
    This class implements our interface to the solr service
    '''

    # TODO: extract this to settings or otherwise
    SOLR_BIN_DIR = '/opt/software/solr/solr-8.9.0/bin'

    # TODO: extract this to settings or otherwise
    SOLR_SERVER = 'http://localhost:8983'

    # relative to the SOLR_SERVER url
    CORES_URL = '/solr/admin/cores'

    # A format-string giving the url for a specific index.
    # Used to initiate queries against an indexed core.
    QUERY_URL = '/solr/{index_name}/select'

    def index(self, index_name, path):
        '''
        Given a local path, index the data in that file.
        '''
        
        # Check if the core exists. If not, we have to create it
        if not self._check_if_core_exists(index_name):
            self._create_core(index_name)

        # index the file:
        cmd = '{bin_dir}/post -c {index_name} {path}'.format(
            bin_dir = self.SOLR_BIN_DIR,
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

    def _check_if_core_exists(self, index_name):
        '''
        Return a boolean indicating whether there is already
        a core with the given name
        '''
        # TODO: implement this check
        return True

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

        cmd = '{bin_dir}/solr create_core -c {index_name} -d {schema_dir}'.format(
            bin_dir = self.SOLR_BIN_DIR,
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
