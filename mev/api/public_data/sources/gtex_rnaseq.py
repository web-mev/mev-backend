import os
import datetime
import pandas as pd
import logging

from django.conf import settings

from api.utilities.basic_utils import make_local_directory, \
    run_shell_command
from api.public_data.sources.base import PublicDataSource

logger = logging.getLogger(__name__)

class GtexRnaseqDataSource(PublicDataSource):

    TAG = 'gtex-rnaseq'
    PUBLIC_NAME = 'GTEx RNA-seq'
    DESCRIPTION = ('Gene read counts for v8 of the GTEx dataset.'
        ' <a href="https://www.gtexportal.org">https://www.gtexportal.org</a>')

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

    # All the GTex data will be stored in this directory
    ROOT_DIR = os.path.join(settings.PUBLIC_DATA_DIR, 'gtex')

    SAMPLE_ATTRIBUTES = 'https://storage.googleapis.com/gtex_analysis_v8/annotations/GTEx_Analysis_v8_Annotations_SampleAttributesDS.txt'
    PHENOTYPES = 'https://storage.googleapis.com/gtex_analysis_v8/annotations/GTEx_Analysis_v8_Annotations_SubjectPhenotypesDS.txt'
    COUNTS = 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/GTEx_Analysis_2017-06-05_v8_RNASeQCv1.1.9_gene_reads.gct.gz'
    
    # The default column names are a bit cryptic, so we rename to something more verbose
    # so it's easier to filter by a user
    COLUMN_MAPPING = {
        'SAMPID': 'sample_id',
        'SMTSD': 'tissue',
        '_SEX': 'sex', # underscore NOT a typo- see below
        'AGE': 'age_range',
        'DTHHRDY':'hardy_scale_death',
        'SMRIN': 'rna_rin',
        'SMNABTCH':'nucleic_acid_isolation_batch',
        'SMGEBTCH':'expression_batch',
        'SMGEBTCHT': 'kit',
        'SMCENTER': 'collection_site_code'
    }

    def __init__(self):
        if not os.path.exists(self.ROOT_DIR):
            logger.info('When instantiating an instance of GtexRnaseqDataSource, the'
                ' expected directory did not exist. Go create it...'
            )
            make_local_directory(self.ROOT_DIR)
        self.date_str = datetime.datetime.now().strftime('%m%d%Y')

    def _download_file(self, url, output):
        '''
        Download a file located at `url` into a filepath given by the 
        `output` arg.
        '''
        download_cmd_template = 'wget {url} -O {output_file}'
        try:
            run_shell_command(download_cmd_template.format(
                url = url,
                output_file = output
            ))
        except Exception as ex:
            logger.info('Failed at downloading from {u}'.format(u=url))
            raise ex

    def prepare(self):
        '''
        Handles prep of the dataset. Does NOT index!
        '''

        # Grab all the required files:
        sample_attr_file = '{d}/samples.{date}.tsv'.format(
            d=self.ROOT_DIR, date=self.date_str)
        phenotypes_file = '{d}/phenotypes.{date}.tsv'.format(
            d=self.ROOT_DIR, date=self.date_str)
        counts_file = '{d}/counts.{date}.gct.gz'.format(
            d=self.ROOT_DIR, date=self.date_str)
        self._download_file(self.SAMPLE_ATTRIBUTES, sample_attr_file)
        self._download_file(self.PHENOTYPES, phenotypes_file)
        self._download_file(self.COUNTS, counts_file)

        # uncompress the counts archive
        run_shell_command('gunzip {f}'.format(f=counts_file))
        counts_file = counts_file[:-3]

        # Merge the sample-level table with the patient-level data
        ann_df = pd.read_table(sample_attr_file, sep='\t')
        pheno_df = pd.read_table(phenotypes_file, sep='\t')
        ann_df['subject_id'] = ann_df['SAMPID'].apply(lambda x: '-'.join(x.split('-')[:2]))
        print(ann_df.head())
        # In the phenotypes file, sex is 2=F, 1=M
        pheno_df['_SEX'] = pheno_df['SEX'].apply(lambda x: 'M' if x==1 else 'F')
        merged_ann = pd.merge(ann_df, pheno_df, left_on='subject_id', right_on='SUBJID')

        # remap the column names and drop the others
        merged_ann.rename(columns=self.COLUMN_MAPPING, inplace=True)
        merged_ann = merged_ann[self.COLUMN_MAPPING.values()]
        merged_ann = merged_ann.set_index('sample_id')

        # at this point we have a prepared annotation table, but it can contain
        # annotations for non-RNA-seq samples. We will use the actual counts to 
        # filter out the non-applicable rows from the annotation file.
        counts = pd.read_table(counts_file, sep='\t', skiprows=2, header=0, index_col=0)
        counts.drop(['Description'], axis=1, inplace=True)
        counts.index = [x.split('.')[0] for x in counts.index]
        samples_from_matrix = counts.columns

        # keep only those rows from the ann matrix that correspond to RNA-seq
        # samples from the matrix
        merged_ann = merged_ann.loc[samples_from_matrix]
        merged_ann.to_csv(
            self.ANNOTATION_OUTPUT_FILE_TEMPLATE.format(
                tag = self.TAG,
                date = self.date_str
            ),
            sep=',',
            index_label = 'sample_id'
        )

        counts_output_path = os.path.join(
            self.ROOT_DIR,
            self.COUNT_OUTPUT_FILE_TEMPLATE.format(
                tag=self.TAG, date=self.date_str
            )
        )
        with pd.HDFStore(counts_output_path) as hdf_out:
            for tissue, subdf in merged_ann.groupby('tissue'):
                group_id = (
                    PublicDataSource.create_python_compatible_id(tissue) + '/ds')
                hdf_out.put(group_id, counts[subdf.index])
                logger.info('Added the {t} matrix to the HDF5'
                    ' count matrix'.format(t=tissue)
                )

    def verify_files(self, file_dict):
        # verifies that all required files are present
        self.check_file_dict(file_dict)

    def get_indexable_files(self, file_dict):
        # Returns a list of files that we should index given
        # the dictionary. Some files do not get indexed, but
        # are necessary for a particular dataset
        # for RNA-seq, we only have to index the annotation file(s)
        return file_dict[self.ANNOTATION_FILE_KEY]

    def get_additional_metadata(self):
        # Returns a dict which contains additional dataset-
        # specific information
        return {}

    def create_from_query(self, database_record, query_params):
        # subsets the dataset based on the query_params.
        # Returns a tuple of a filepath (string) and
        # a resource_type
        pass
