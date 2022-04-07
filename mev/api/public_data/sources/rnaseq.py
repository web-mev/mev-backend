import os
import uuid
import json
import datetime
import pandas as pd
import logging

from django.conf import settings

from api.utilities.basic_utils import make_local_directory

class RnaSeqMixin(object):

    # A common feature of RNA-seq is that we will have annotation
    # and count files
    ANNOTATION_FILE_KEY = 'annotations'
    COUNTS_FILE_KEY = 'counts'
    DATASET_FILES = [
        ANNOTATION_FILE_KEY,
        COUNTS_FILE_KEY
    ]

    # A format-string for the annotation file
    ANNOTATION_OUTPUT_FILE_TEMPLATE = 'annotations.{tag}.{date}.csv'

    # A format-string for the count file
    COUNT_OUTPUT_FILE_TEMPLATE = 'counts.{tag}.{date}.hd5'

    @staticmethod
    def create_python_compatible_id(id):
        '''
        When adding datasets or groups to a HDF5 file, we need to modify
        the name or it will not address properly. Identifiers like
        "Whole Blood" do not work, but whole_blood does.
        '''
        return id.replace('-', '_').replace(' ','_').replace('(','_').replace(')','_').lower()

    def get_indexable_files(self, file_dict):

        # for RNA-seq, we only have to index the annotation file(s)
        return file_dict[self.ANNOTATION_FILE_KEY]

    def create_from_query(self, database_record, query_filter, output_name=''):
        '''
        subsets the dataset based on the query_filter.
        Returns a 3-tuple of lists:
        - a list of paths
        - a list of names for the files 
        - a list of resource types
        '''
        # Look at the database object to get the path for the count matrix
        file_mapping = database_record.file_mapping
        count_matrix_path = file_mapping[self.COUNTS_FILE_KEY][0]
        if not os.path.exists(count_matrix_path):
            #TODO: better error handling here.
            logger.info('Could not find the count matrix')
            raise Exception('Failed to find the proper data for this'
                ' request. An administrator has been notified'
            )

        # if the query_filter was None (indicating no filtering was desired)
        # then we reject-- this dataset is too big to store as a single
        # dataframe
        if query_filter is None:
            raise Exception('The {name} dataset is too large to request without'
                ' any filters. Please try again and request a'
                ' subset of the data.'.format(name = self.PUBLIC_NAME)
            )

        # to properly filter our full HDF5 matrix, we expect a data structure that
        # looks like:
        #
        # {'tissue A': [<sample ID>, <sample ID>], 'tissue B': [<sample ID>]}
        #
        # The top level contains identifiers which we use to select
        # the groups within the HDF5 file. Then, we use the sample IDs to filter the
        # dataframes
        final_df = pd.DataFrame()
        with pd.HDFStore(count_matrix_path, 'r') as hdf:
            for ct in query_filter.keys():
                if not type(query_filter[ct]) is list:
                    raise Exception('Problem encountered with the filter'
                        ' provided. We expect each cancer type to address'
                        ' a list of sample identifiers, such as: {j}'.format(
                            j = json.dumps(self.EXAMPLE_PAYLOAD)
                        )
                    )
                group_id = RnaSeqMixin.create_python_compatible_id(ct) + '/ds'
                try:
                    df = hdf.get(group_id)
                except KeyError as ex:
                    raise Exception('The requested project'
                        ' {ct} was not found in the dataset. Ensure your'
                        ' request was correctly formatted.'.format(ct=ct)
                    )
                try:
                    df = df[query_filter[ct]]
                except KeyError as ex:
                    message = ('The subset of the count matrix failed since'
                        ' one or more requested samples were missing: {s}'.format(
                            s = str(ex)
                        )
                    )
                    raise Exception(message)

                final_df = pd.concat([final_df, df], axis=1)

        if final_df.shape[1] == 0:
            raise Exception('The resulting matrix was empty. No'
                ' data was created.'
            )

        # write the file to a temp location:
        filename = '{u}.tsv'.format(u=str(uuid.uuid4()))
        dest_dir = os.path.join(settings.DATA_DIR, 'tmp')
        if not os.path.exists(dest_dir):
            make_local_directory(dest_dir)
        count_filepath = os.path.join(dest_dir, filename)
        try:
            final_df.to_csv(count_filepath, sep='\t')
        except Exception as ex:
            logger.info('Failed to write the subset of GDC RNA-seq'
                ' Exception was: {ex}'.format(ex=ex)
            )
            raise Exception('Failed when writing the filtered data.')

        # now create the annotation file:
        full_uuid_list = []
        [full_uuid_list.extend(query_filter[k]) for k in query_filter.keys()]
        ann_path = file_mapping[self.ANNOTATION_FILE_KEY][0]
        if not os.path.exists(ann_path):
            #TODO: better error handling here.
            logger.info('Could not find the annotation matrix')
            raise Exception('Failed to find the proper data for this'
                ' request. An administrator has been notified'
            )
        ann_df = pd.read_csv(ann_path, index_col=0)
        subset_ann = ann_df.loc[full_uuid_list]

        # drop columns which are completely empty:
        subset_ann = subset_ann.dropna(axis=1, how='all')

        filename = '{u}.tsv'.format(u=str(uuid.uuid4()))

        ann_filepath = os.path.join(dest_dir, filename)
        try:
            subset_ann.to_csv(ann_filepath, sep='\t')
        except Exception as ex:
            logger.info('Failed to write the subset of the annotation dataframe.'
                ' Exception was: {ex}'.format(ex=ex)
            )
            raise Exception('Failed when writing the filtered annotation data.')

        # finally make some names for these files, which we return
        if output_name == '':
            u = str(uuid.uuid4())
            count_matrix_name = self.TAG + '_counts.' + u + '.tsv'
            ann_name = self.TAG + '_ann.' + u + '.tsv'
        else:
            count_matrix_name = output_name + '_counts.' + self.TAG + '.tsv'
            ann_name = output_name + '_ann.' + self.TAG + '.tsv'
        return [count_filepath, ann_filepath], \
                [count_matrix_name, ann_name], \
                ['RNASEQ_COUNT_MTX', 'ANN']