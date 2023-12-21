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
            if not type(filepaths) is list:
                raise Exception('Each key of the passed dictionary'
                    ' should address a list of file paths. The offending key'
                    ' was {k}'.format(k=file_key)
                )
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

    def get_additional_metadata(self):
        raise NotImplementedError('Must implement this method in a child class.')

    def create_from_query(self, db_record, query_params):
        raise NotImplementedError('Must implement this method in a child class.')

    def apply_additional_filters(self, *args, **kwargs):
        '''
        This method is used during dataset creation (e.g. a user has filtered
        down to a cohort of interest and would like to save that data)
        following filtering of the annotations and values
        (e.g. rna-seq counts, etc.). It allows us to act on additional filters
        which are provided by the `query_filter` arg.

        Since each public dataset can have different implementations of this,
        we leave that to the child classes. To ensure compliance with this spec
        we raise the NotImplementedError exception in this base class.
        '''
        raise NotImplementedError('Must implement this method in a child class.')
