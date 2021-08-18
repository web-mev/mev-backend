class BaseIndexer(object):
    '''
    This is a base class from which all data indexers will derive.

    Indexers allow the data to be prepared for query and each implementation
    may do this differently.
    '''

    def index(self, index_name, path):
        raise NotImplementedError('Must implement this method in a child class.')