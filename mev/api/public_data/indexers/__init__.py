from django.conf import settings

from api.public_data.indexers.solr import SolrIndexer

INDEXER_CHOICES = {
    'solr': SolrIndexer
}

def get_indexer():
    '''
    Returns an instance of the class
    which implements the chosen indexer (as provided in 
    the Django settings)

    In the settings module, we have already checked that a valid
    setting has been selected for the indexer, so we don't have
    to guard against garbage here.
    '''
    return INDEXER_CHOICES[settings.PUBLIC_DATA_INDEXER]()
        
