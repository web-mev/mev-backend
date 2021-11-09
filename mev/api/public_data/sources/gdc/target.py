import logging
import datetime
import os
 
from django.conf import settings

from api.utilities.basic_utils import make_local_directory

from .gdc import GDCDataSource, GDCRnaSeqDataSourceMixin

logger = logging.getLogger(__name__)

class TargetDataSource(GDCDataSource):
    '''
    A general class for pulling data from TARGET, exposed via the GDC API
    '''

    # All the TCGA-based data will be stored in this directory
    ROOT_DIR = os.path.join(settings.PUBLIC_DATA_DIR, 'target')

    def __init__(self):
        if not os.path.exists(self.ROOT_DIR):
            logger.info('When instantiating an instance of TARGETDataSource, the'
                ' expected directory did not exist. Go create it...'
            )
            make_local_directory(self.ROOT_DIR)

    def download_and_prep_dataset(self):
        pass

    def get_additional_metadata(self):
        '''
        For the TCGA datasets, we would like an additional mapping from the shorthand ID 
        (e.g. TCGA-LUAD) to the "full" name (e.g. lung adenocarcinoma) 
        '''
        mapping = self.query_for_project_names_within_program('TARGET')
        return {'target_type_to_name_map': mapping}


class TargetRnaSeqDataSource(TargetDataSource, GDCRnaSeqDataSourceMixin):
    '''
    A specific implementation of the TARGET data source specific to
    RNA-seq.
    '''

    # A short name (string) which can be used as a "title" for the dataset
    PUBLIC_NAME = 'TARGET RNA-Seq'

    # A longer, more descriptive text explaining the datasource:
    DESCRIPTION = ('TARGET RNA-Seq expression data as processed by the'
        ' Genomic Data Commons'
        ' <a href="https://docs.gdc.cancer.gov/Data/Bioinformatics_Pipelines/Expression_mRNA_Pipeline/">'
        ' mRNA analysis pipeline</a>. Quantifications from this pipeline'
        ' are produced by HTSeq.'
    )

    # a string which will make it obvious where the data has come from. For example, we can use
    # this tag to name an output file produced by this class (e.g. the count matrix).
    # We also use this tag
    TAG = 'target-rnaseq'

    # An example of how one might query this dataset, so we can provide useful
    # help for dataset creation errors:
    EXAMPLE_PAYLOAD = {
        'TARGET-AML': ["<UUID>","<UUID>"],
        'TARGET-NBL': ["<UUID>","<UUID>", "<UUID>"]
    }

    def __init__(self):
        super().__init__()
        self.date_str = datetime.datetime.now().strftime('%m%d%Y')

    def prepare(self):
        '''
        Entry method for downloading and munging the TCGA RNA-seq dataset
        to a HDF5 file
        '''
        self._pull_data('TARGET', self.TAG)

    def get_additional_metadata(self):
        '''
        This just uses the parent method which maps the TCGA IDs to
        the name (e.g. TARGET-AML --> Acute Myeloid Leukemia)
        '''
        # uses the get_additional_metadata method of TargetDataSource
        # per python's MRO
        return super().get_additional_metadata()