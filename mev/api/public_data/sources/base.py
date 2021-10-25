import os

class PublicDataSource(object):
    
    def prepare(self):
        raise NotImplementedError('Must implement this method in a child class.')

    def check_file_dict(self, file_dict):
        '''
        A common method that can be used by child classes for verifying
        that the passed `file_dict` has the proper members AND that the
        files exist.

        `file_dict` is a dictionary with string keys and list values.
        Each string item in those lists should be a valid file path.
        '''

        # check that we have all the necessary files. Extras are just
        # ignored
        s1 = set(file_dict.keys())
        s2 = set(self.DATASET_FILES)
        diff_set = s2.difference(s1)
        if len(diff_set) > 0:
            raise Exception('Missing the following required files for'
                ' this dataset: {v}'.format(v = ','.join(diff_set))
            )

        for file_key in self.DATASET_FILES:
            filepaths = file_dict[file_key]
            for f in filepaths:
                if not os.path.exists(f):
                    message = ('The file {f} corresponding to key "{k}" did not exist.'
                    ' Check the path. Exiting.'.format(
                            f = f,
                            k = file_key
                        )
                    )
                    raise Exception(message)

    def verify_files(self, file_dict):
        raise NotImplementedError('Must implement this method in a child class.')

    def get_indexable_files(self, file_dict):
        raise NotImplementedError('Must implement this method in a child class.')

    def create_from_query(self, query_params):
        raise NotImplementedError('Must implement this method in a child class.')