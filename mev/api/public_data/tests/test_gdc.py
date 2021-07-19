import unittest
import unittest.mock as mock
import json
import os
import datetime

from django.conf import settings

from api.public_data.gdc.gdc import GDCDataSource
from api.public_data.gdc.tcga import TCGADataSource, TCGARnaSeqDataSource


class TestGDC(unittest.TestCase): 
    def test_dummy(self):
        self.assertTrue(True)


class TestTCGA(unittest.TestCase): 
    def test_dummy(self):
        self.assertTrue(True)


class TestTCGARnaSeq(unittest.TestCase): 

    def test_proper_filters_created(self):
        '''
        Tests that the json payload for a metadata
        query is created as expected
        '''
        ds = TCGARnaSeqDataSource()
        d = ds._create_filters()

        # Note that in the dict below, the value of the 'filters' key is itself a JSON
        # format string. The GDC API will not accept if that value happened to be a native
        # python dict
        expected_query_filters = {
            "fields": "file_id,file_name,cases.project.program.name,cases.case_id,cases.aliquot_ids,cases.samples.portions.analytes.aliquots.aliquot_id",
            "format": "JSON",
            "size": "100",
            "expand": "cases.demographic,cases.diagnoses,cases.exposures,cases.tissue_source_site,cases.project",
            "filters": "{\"op\": \"and\", \"content\": [{\"op\": \"in\", \"content\": {\"field\": \"files.cases.project.program.name\", \"value\": [\"TCGA\"]}}, {\"op\": \"in\", \"content\": {\"field\": \"files.analysis.workflow_type\", \"value\": [\"HTSeq - Counts\"]}}, {\"op\": \"in\", \"content\": {\"field\": \"files.experimental_strategy\", \"value\": [\"RNA-Seq\"]}}, {\"op\": \"in\", \"content\": {\"field\": \"files.data_type\", \"value\": [\"Gene Expression Quantification\"]}}]}"
        }
        self.assertDictEqual(d, expected_query_filters)


    @mock.patch('api.public_data.gdc.tcga.TCGARnaSeqDataSource.ANNOTATION_OUTPUT_FILE', '__TEST__annotations.{tag}.{ds}.tsv')
    @mock.patch('api.public_data.gdc.tcga.TCGARnaSeqDataSource.COUNT_OUTPUT_FILE', '__TEST__counts.{tag}.{ds}.tsv')
    @mock.patch('api.public_data.gdc.tcga.TCGARnaSeqDataSource._create_filters')
    @mock.patch('api.public_data.gdc.tcga.datetime')
    def test_download_works(self, mock_datetime, mock_create_filters):
        '''
        This may not be an official unit test as it actually does communicate out
        to the GDC api.
        '''
        # This filter is the same as in the class, except that it adds an additional
        # filter on the TCGA cancer types
        query_filters = {
            "fields": "file_id,file_name,cases.project.program.name,cases.case_id,cases.aliquot_ids,cases.samples.portions.analytes.aliquots.aliquot_id",
            "format": "JSON",
            "size": "100",
            "expand": "cases.demographic,cases.diagnoses,cases.exposures,cases.tissue_source_site,cases.project",
            "filters": "{\"op\": \"and\", \"content\": [{\"op\": \"in\", \"content\": {\"field\": \"files.cases.project.program.name\", \"value\": [\"TCGA\"]}}, {\"op\": \"in\", \"content\": {\"field\": \"files.cases.project.project_id\", \"value\": [\"TCGA-UVM\", \"TCGA-MESO\"]}}, {\"op\": \"in\", \"content\": {\"field\": \"files.analysis.workflow_type\", \"value\": [\"HTSeq - Counts\"]}}, {\"op\": \"in\", \"content\": {\"field\": \"files.experimental_strategy\", \"value\": [\"RNA-Seq\"]}}, {\"op\": \"in\", \"content\": {\"field\": \"files.data_type\", \"value\": [\"Gene Expression Quantification\"]}}]}"
        }   
        mock_create_filters.return_value = query_filters
        data_src = TCGARnaSeqDataSource()

        now = datetime.datetime.now()
        mock_datetime.datetime.now.return_value = now

        data_src.download_dataset()

        expected_output_annotation_file = os.path.join(
            TCGADataSource.ROOT_DIR,
            TCGARnaSeqDataSource.ANNOTATION_OUTPUT_FILE.format(
                tag = TCGARnaSeqDataSource.TAG,
                ds = now.strftime('%m%d%Y')
            )
        )
        expected_output_count_file = os.path.join(
            TCGADataSource.ROOT_DIR,
            TCGARnaSeqDataSource.COUNT_OUTPUT_FILE.format(
                tag = TCGARnaSeqDataSource.TAG,
                ds = now.strftime('%m%d%Y')
            )
        )
        self.assertTrue(os.path.exists(expected_output_annotation_file))
        self.assertTrue(os.path.exists(expected_output_count_file))

        # cleanup those files:
        os.remove(expected_output_count_file)
        os.remove(expected_output_annotation_file)
      
