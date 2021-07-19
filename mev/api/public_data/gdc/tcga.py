import copy
import re
import json
import logging
import requests
import datetime
import shutil
import os
import tarfile

import pandas as pd

from django.conf import settings

from api.utilities.basic_utils import get_with_retry, make_local_directory

from .gdc import GDCDataSource

logger = logging.getLogger(__name__)

class TCGADataSource(GDCDataSource):
    '''
    A general class for pulling data from TCGA, exposed via the GDC API
    '''

    # All the TCGA-based data will be stored in this directory
    ROOT_DIR = os.path.join(settings.PUBLIC_DATA_DIR, 'tcga')

    # This list helps to define the full filter used in the child classes.
    # Each item in this list (dicts) conforms to the GDC query syntax. We
    # don't implement checks for valid queries here, but rather rely on the GDC
    # API
    # Note that any items here will ultimately be "concatenated" using a logical
    # AND operation
    FILTER_LIST = [
        {
            "op": "in",
            "content":{
                "field": "files.cases.project.program.name",
                "value": ["TCGA"]
                }
        }
    ]

    def __init__(self):
        if not os.path.exists(self.ROOT_DIR):
            logger.info('When instantiating an instance of TCGADataSource, the'
                ' expected directory did not exist. Go create it...'
            )
            make_local_directory(self.ROOT_DIR)

    def download_dataset(self):
        pass


class TCGARnaSeqDataSource(TCGADataSource):
    '''
    A specific implementation of the TCGA data source specific to
    RNA-seq.
    '''

    # We look for HTSeq-based counts from TCGA
    HTSEQ_SUFFIX = 'htseq.counts.gz'

    # a string which will make it obvious where the data has come from. For example, we can use
    # this tag to name an output file produced by this class (e.g. the count matrix)
    TAG = 'tcga-rnaseq'

    # A format-string for the annotation file
    ANNOTATION_OUTPUT_FILE = 'annotations.{tag}.{ds}.tsv'

    # A format-string for the count file
    COUNT_OUTPUT_FILE = 'counts.{tag}.{ds}.tsv'

    # This list defines further filters which are specific to this class where we
    # are getting data regarding HTSeq-based RNA-seq counts. This list is in addition
    # to any other FILTER_LIST class attributes defined in parent classes. We will
    # ultimately combine them using a local AND to create the final filter for our query
    # to the GDC API.
    FILTER_LIST = [
        {
            "op": "in",
            "content":{
                "field": "files.analysis.workflow_type",
                "value": ["HTSeq - Counts"]
                }
        },
        {
            "op": "in",
            "content":{
                "field": "files.experimental_strategy",
                "value": ["RNA-Seq"]
                }
        },
        {
            "op": "in",
            "content":{
                "field": "files.data_type",
                "value": ["Gene Expression Quantification"]
                }
        }
    ]
    

    # The count files include counts to non-genic features. We don't want those
    # in our final assembled count matrix
    SKIPPED_FEATURES = [
        '__no_feature', 
        '__ambiguous',
        '__too_low_aQual', 
        '__not_aligned', 
        '__alignment_not_unique'
    ]

    def _create_filters(self):
        '''
        Internal method to create the GDC-compatible filter syntax
        '''
        final_filter_list = []
        final_filter_list.extend(TCGADataSource.FILTER_LIST)
        final_filter_list.extend(self.FILTER_LIST)

        final_filter = {
            'op': 'and',
            'content': final_filter_list
        }

        final_query_params = copy.deepcopy(GDCDataSource.QUERY_PARAMS)

        # The query format requires that the nested items are already serialized
        # to JSON format. e.g. if `final_filter` were to remain a native python
        # dict, then the request would fail. 
        final_query_params['filters'] = json.dumps(final_filter)
        return final_query_params

    def download_dataset(self):
        '''
        Implementation of the RNA-seq data download
        '''

        # Get the data dictionary, which will tell us the universe of available
        # fields and how to interpret them:
        data_fields = self.get_data_dictiontary()

        final_query_params = self._create_filters()
        
        # prepare some temporary loop variables
        finished = False
        i = 0
        downloaded_archives = []

        # We have to keep a map of the fileId to the aliquot so we can properly 
        # concatenate the files later
        file_to_aliquot_mapping = {}
        annotation_df = pd.DataFrame()
        while not finished:
            logger.info('Downloading TCGA RNA-seq batch %d ...' % i)

            # the records are paginated, so we have to keep track of which page we are currently requesting
            start_index = i*GDCDataSource.PAGE_SIZE
            end_index = (i+1)*GDCDataSource.PAGE_SIZE
            final_query_params.update(
                {
                    'from': start_index
                }
            )
            print(final_query_params)
            print('*'*200)
            try:
                response = get_with_retry(
                    GDCDataSource.GDC_FILES_ENDPOINT, 
                    params = final_query_params
                )
            except Exception as ex:
                logger.info('An exception was raised when querying the GDC for'
                    ' metadata. The exception reads: {ex}'.format(ex=ex)
                )
                return

            if response.status_code == 200:
                response_json = json.loads(response.content.decode("utf-8"))
            else:
                logger.error('The response code was NOT 200, but the request'
                    ' exception was not handled.'
                )
                return

            # If the first request, we can get the total records by examining
            # the pagination data
            if i == 0:
                pagination_response = response_json['data']['pagination']
                total_records = int(pagination_response['total'])

            # now collect the file UUIDs and download
            file_uuid_list = []
            case_id_list = []
            exposures = []
            diagnoses = []
            demographics = []
            projects = []
            aliquot_ids = []

            for hit in response_json['data']['hits']:
                file_uuid_list.append(hit['file_id'])

                # hit['cases'] is a list. To date, have only seen length of 1, 
                # and it's not clear what a greater length would mean.
                # Hence, catch this and issue an error so we can investigate
                if len(hit['cases']) > 1:
                    logger.error('Encountered an unexpected issue when iterating through the returned hits'
                        ' of a TCGA RNA-seq query. We expect the "cases" key for a hit to be of length 1,'
                        ' but this was greater. Returned data was: {k}'.format(k=json.dumps(response_json))
                    )
                    return

                case_item = hit['cases'][0]
                case_id_list.append(case_item['case_id'])

                try:
                    exposures.append(case_item['exposures'][0])
                except KeyError as ex:
                    exposures.append({})

                try:
                    diagnoses.append(case_item['diagnoses'][0])
                except KeyError as ex:
                    diagnoses.append({})

                try:
                    demographics.append(case_item['demographic'])
                except KeyError as ex:
                    demographics.append({})

                try:
                    projects.append(case_item['project'])
                except KeyError as ex:
                    projects.append({})

                try:
                    aliquot_ids.append(case_item['samples'][0]['portions'][0]['analytes'][0]['aliquots'][0]['aliquot_id'])
                except KeyError as ex:
                    # Need an aliquot ID to uniquely identify the column. Fail out
                    logger.error('Encountered an unexpected issue when iterating through the returned hits'
                        ' of a TCGA RNA-seq query. We expect that we should be able to drill-down to find a unique aliquot ID.'
                        ' The returned data was: {k}'.format(k=json.dumps(response_json))
                    )
                    return

            file_to_aliquot_mapping.update(dict(zip(file_uuid_list, aliquot_ids)))

            exposure_df = GDCDataSource.merge_with_full_record(
                data_fields['exposure'], 
                exposures, 
                aliquot_ids
            )

            demographic_df = GDCDataSource.merge_with_full_record(
                data_fields['demographic'], 
                demographics, 
                aliquot_ids
            )

            diagnoses_df = GDCDataSource.merge_with_full_record(
                data_fields['diagnosis'], 
                diagnoses, 
                aliquot_ids
            )

            # note that we keep the extra 'project_id' field in this method call. 
            # That gives us the cancer type such as "TCGA-BRCA", etc.
            project_df = GDCDataSource.merge_with_full_record(
                data_fields['project'], 
                projects, 
                aliquot_ids,
                extra_fields = ['project_id']
            )

            # Remove the extra project_id column from the exposure, demo, and diagnoses dataframes. Otherwise we get duplicated
            # columns that we have to carry around:
            exposure_df = exposure_df.drop('project_id', axis=1)
            diagnoses_df = diagnoses_df.drop('project_id', axis=1)
            demographic_df = demographic_df.drop('project_id', axis=1)

            # Now merge all the dataframes (concatenate horizontally)
            # to get the full metadata/annotations
            ann_df = pd.concat([
                exposure_df,
                demographic_df,
                diagnoses_df,
                project_df
            ], axis=1)

            # Create another series which maps the aliquot IDs to the case ID.
            # That will then be added to the annotation dataframe so we know which 
            # metadata is mapped to each case
            s = pd.Series(dict(zip(aliquot_ids, case_id_list)), name='case_id')

            ann_df = pd.concat([ann_df, s], axis=1)

            # Add to the master dataframe
            annotation_df = pd.concat([annotation_df, ann_df], axis=0)

            # Download the actual expression data corresponding to the aliquot metadata
            # we've been collecting
            download_params = {"ids": file_uuid_list}
            download_response = requests.post(GDCDataSource.GDC_DATA_ENDPOINT, 
                data = json.dumps(download_params), 
                headers = {"Content-Type": "application/json"}
            )
            response_head_cd = download_response.headers["Content-Disposition"]
            file_name = re.findall("filename=(.+)", response_head_cd)[0]
            with open(file_name, "wb") as output_file:
                output_file.write(download_response.content)
            downloaded_archives.append(file_name)

            i += 1

            # are we done yet???
            if end_index >= total_records:
                finished = True

        # Write all the metadata to a file
        date_str = datetime.datetime.now().strftime('%m%d%Y')
        annotation_df.to_csv(
            os.path.join(
                self.ROOT_DIR,
                self.ANNOTATION_OUTPUT_FILE.format(tag = self.TAG, ds=date_str)
            ), 
            sep=',', 
            index_label = 'id'
        )

        # Merge and write the count files
        self._merge_downloaded_archives(downloaded_archives, file_to_aliquot_mapping, date_str)

        # Cleanup the downloads
        [os.remove(x) for x in downloaded_archives]


    def _merge_downloaded_archives(self, downloaded_archives, file_to_aliquot_mapping, date_str):
        '''
        Given a list of the downloaded archives, extract and merge them into a single count matrix
        '''
        count_df = pd.DataFrame()
        tmpdir = os.path.join(self.ROOT_DIR, 'tmparchive')
        for f in downloaded_archives:
            with tarfile.open(f, 'r:gz') as tf:
                tf.extractall(path=tmpdir)
                for t in tf.getmembers():
                    if t.name.endswith(self.HTSEQ_SUFFIX):
                        file_id = t.name.split('/')[0]
                        df = pd.read_table(
                            os.path.join(tmpdir, t.path), 
                            index_col=0, 
                            header=None, 
                            names=['gene', file_to_aliquot_mapping[file_id]])
                        count_df = pd.concat([count_df, df], axis=1)

        # remove the skipped rows which don't correspond to actual gene features
        count_df = count_df.loc[~count_df.index.isin(self.SKIPPED_FEATURES)]
        count_df.to_csv(
            os.path.join(
                self.ROOT_DIR,
                self.COUNT_OUTPUT_FILE.format(tag=self.TAG, ds=date_str)
            ), 
            sep='\t'
        )

        # Clean up:
        shutil.rmtree(tmpdir)
