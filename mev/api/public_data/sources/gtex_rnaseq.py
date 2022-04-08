import os
import datetime
import pandas as pd
import logging
import uuid

from django.conf import settings

from api.utilities.basic_utils import make_local_directory, \
    run_shell_command
from api.public_data.sources.base import PublicDataSource
from api.public_data.sources.rnaseq import RnaSeqMixin

logger = logging.getLogger(__name__)

class GtexRnaseqDataSource(PublicDataSource, RnaSeqMixin):

    TAG = 'gtex-rnaseq'
    PUBLIC_NAME = 'GTEx RNA-seq'
    DESCRIPTION = ('Gene read counts for v8 of the GTEx dataset.'
        ' <a href="https://www.gtexportal.org">https://www.gtexportal.org</a>')

    # An example of how one might query this dataset, so we can provide useful
    # help for dataset creation errors:
    EXAMPLE_PAYLOAD = {
        'Whole Blood': ["<ID>","<ID>"],
        'Prostate': ["<ID>","<ID>", "<ID>"]
    }

    # All the GTex data will be stored in this directory
    ROOT_DIR = os.path.join(settings.PUBLIC_DATA_DIR, 'gtex')

    SAMPLE_ATTRIBUTES = 'https://storage.googleapis.com/gtex_analysis_v8/annotations/GTEx_Analysis_v8_Annotations_SampleAttributesDS.txt'
    PHENOTYPES = 'https://storage.googleapis.com/gtex_analysis_v8/annotations/GTEx_Analysis_v8_Annotations_SubjectPhenotypesDS.txt'
    TISSUE_TO_FILE_MAP = {
        'Adipose - Subcutaneous': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_adipose_subcutaneous.gct.gz',
        'Adipose - Visceral (Omentum)': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_adipose_visceral_omentum.gct.gz',
        'Adrenal Gland': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_adrenal_gland.gct.gz',
        'Artery - Aorta': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_artery_aorta.gct.gz',
        'Artery - Coronary': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_artery_coronary.gct.gz',
        'Artery - Tibial': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_artery_tibial.gct.gz',
        'Bladder': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_bladder.gct.gz',
        'Brain - Amygdala': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_brain_amygdala.gct.gz',
        'Brain - Anterior cingulate cortex (BA24)': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_brain_anterior_cingulate_cortex_ba24.gct.gz',
        'Brain - Caudate (basal ganglia)': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_brain_caudate_basal_ganglia.gct.gz',
        'Brain - Cerebellar Hemisphere': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_brain_cerebellar_hemisphere.gct.gz',
        'Brain - Cerebellum': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_brain_cerebellum.gct.gz',
        'Brain - Cortex': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_brain_cortex.gct.gz',
        'Brain - Frontal Cortex (BA9)': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_brain_frontal_cortex_ba9.gct.gz',
        'Brain - Hippocampus': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_brain_hippocampus.gct.gz',
        'Brain - Hypothalamus': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_brain_hypothalamus.gct.gz',
        'Brain - Nucleus accumbens (basal ganglia)': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_brain_nucleus_accumbens_basal_ganglia.gct.gz',
        'Brain - Putamen (basal ganglia)': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_brain_putamen_basal_ganglia.gct.gz',
        'Brain - Spinal cord (cervical c-1)': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_brain_spinal_cord_cervical_c-1.gct.gz',
        'Brain - Substantia nigra': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_brain_substantia_nigra.gct.gz',
        'Breast - Mammary Tissue': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_breast_mammary_tissue.gct.gz',
        'Cells - Cultured fibroblasts': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_cells_cultured_fibroblasts.gct.gz',
        'Cells - EBV-transformed lymphocytes': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_cells_ebv-transformed_lymphocytes.gct.gz',
        'Cervix - Ectocervix': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_cervix_ectocervix.gct.gz',
        'Cervix - Endocervix': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_cervix_endocervix.gct.gz',
        'Colon - Sigmoid': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_colon_sigmoid.gct.gz',
        'Colon - Transverse': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_colon_transverse.gct.gz',
        'Esophagus - Gastroesophageal Junction': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_esophagus_gastroesophageal_junction.gct.gz',
        'Esophagus - Mucosa': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_esophagus_mucosa.gct.gz',
        'Esophagus - Muscularis': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_esophagus_muscularis.gct.gz',
        'Fallopian Tube': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_fallopian_tube.gct.gz',
        'Heart - Atrial Appendage': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_heart_atrial_appendage.gct.gz',
        'Heart - Left Ventricle': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_heart_left_ventricle.gct.gz',
        'Kidney - Cortex': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_kidney_cortex.gct.gz',
        'Kidney - Medulla': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_kidney_medulla.gct.gz',
        'Liver': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_liver.gct.gz',
        'Lung': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_lung.gct.gz',
        'Minor Salivary Gland': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_minor_salivary_gland.gct.gz',
        'Muscle - Skeletal': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_muscle_skeletal.gct.gz',
        'Nerve - Tibial': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_nerve_tibial.gct.gz',
        'Ovary': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_ovary.gct.gz',
        'Pancreas': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_pancreas.gct.gz',
        'Pituitary': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_pituitary.gct.gz',
        'Prostate': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_prostate.gct.gz',
        'Skin - Not Sun Exposed (Suprapubic)': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_skin_not_sun_exposed_suprapubic.gct.gz',
        'Skin - Sun Exposed (Lower leg)': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_skin_sun_exposed_lower_leg.gct.gz',
        'Small Intestine - Terminal Ileum': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_small_intestine_terminal_ileum.gct.gz',
        'Spleen': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_spleen.gct.gz',
        'Stomach': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_stomach.gct.gz',
        'Testis': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_testis.gct.gz',
        'Thyroid': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_thyroid.gct.gz',
        'Uterus': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_uterus.gct.gz',
        'Vagina': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_vagina.gct.gz',
        'Whole Blood': 'https://storage.googleapis.com/gtex_analysis_v8/rna_seq_data/gene_reads/gene_reads_2017-06-05_v8_whole_blood.gct.gz'
    }
    
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
        print('in init with self.ROOT_DIR=', self.ROOT_DIR)
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

    def _get_sample_annotations(self, tmp_dir):
        sample_attr_file = '{d}/samples.{tag}.{date}.tsv'.format(
            d=tmp_dir, date=self.date_str, tag=self.TAG)
        self._download_file(self.SAMPLE_ATTRIBUTES, sample_attr_file)
        return pd.read_table(sample_attr_file, sep='\t')

    def _get_phenotype_data(self, tmp_dir):
        phenotypes_file = '{d}/phenotypes.{tag}.{date}.tsv'.format(
            d=tmp_dir, date=self.date_str, tag=self.TAG)
        self._download_file(self.PHENOTYPES, phenotypes_file)
        return pd.read_table(phenotypes_file, sep='\t')

    def _create_tmp_dir(self):
        '''
        Create a temporary directory where we munge all the files
        '''
        folder_name = 'tmp-{u}'.format(u=uuid.uuid4())
        tmp_dir = os.path.join(settings.DATA_DIR, folder_name)
        if not os.path.exists(tmp_dir):
            make_local_directory(tmp_dir)
        return tmp_dir

    def prepare(self):
        '''
        Handles prep of the dataset. Does NOT index!
        '''
        tmp_dir = self._create_tmp_dir()

        ann_df = self._get_sample_annotations(tmp_dir)
        pheno_df = self._get_phenotype_data(tmp_dir)

        # Merge the sample-level table with the patient-level data
        ann_df['subject_id'] = ann_df['SAMPID'].apply(lambda x: '-'.join(x.split('-')[:2]))

        # In the phenotypes file, sex is 2=F, 1=M
        pheno_df['_SEX'] = pheno_df['SEX'].apply(lambda x: 'M' if x==1 else 'F')
        merged_ann = pd.merge(ann_df, pheno_df, left_on='subject_id', right_on='SUBJID')

        # remap the column names and drop the others
        merged_ann.rename(columns=self.COLUMN_MAPPING, inplace=True)
        merged_ann = merged_ann[self.COLUMN_MAPPING.values()]
        merged_ann = merged_ann.set_index('sample_id')

        final_ann = pd.DataFrame()
        counts_output_path = os.path.join(
            self.ROOT_DIR,
            self.COUNT_OUTPUT_FILE_TEMPLATE.format(
                tag=self.TAG, date=self.date_str
            )
        )
        with pd.HDFStore(counts_output_path) as hdf_out:
            for i, (tissue, tissue_subdf) in enumerate(merged_ann.groupby('tissue')):
                logger.info('Handling tissue {t}'.format(t=tissue))
                url = self.TISSUE_TO_FILE_MAP[tissue]
                output_file = '{d}/f{i}.gct.gz'.format(d=tmp_dir, i=i)
                self._download_file(url, output_file)
                run_shell_command('gunzip {f}'.format(f=output_file))
                output_file = output_file[:-3]

                # the GCT-format file has two header lines. The third line has the usual
                # column headers
                counts = pd.read_table(output_file, sep='\t', skiprows=2, header=0, index_col=1)
                counts.drop(['Description'], axis=1, inplace=True)
                counts.drop(['id'], axis=1, inplace=True)
                # Remove the version from the ENSG gene ID
                counts.index = [x.split('.')[0] for x in counts.index]

                samples_in_matrix = counts.columns
                tissue_subdf = tissue_subdf.loc[samples_in_matrix]
                final_ann = pd.concat([final_ann, tissue_subdf], axis=0)

                group_id = RnaSeqMixin.create_python_compatible_id(tissue) + '/ds'
                hdf_out.put(group_id, counts)

        final_ann.to_csv(
            self.ANNOTATION_OUTPUT_FILE_TEMPLATE.format(
                tag = self.TAG,
                date = self.date_str
            ),
            sep=',',
            index_label = 'sample_id'
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

    

