import unittest
import os

from api.data_structures import Observation, \
    ObservationSet, \
    Feature, \
    FeatureSet, \
    StringAttribute, \
    IntegerAttribute

from api.serializers.observation_set import ObservationSetSerializer
from api.serializers.feature_set import FeatureSetSerializer
from api.resource_types.table_types import TableResource, \
    Matrix, \
    IntegerMatrix, \
    AnnotationTable, \
    FeatureTable, \
    BEDFile

# the api/tests dir
TESTDIR = os.path.dirname(__file__)
TESTDIR = os.path.join(TESTDIR, 'resource_validation_test_files')

class TestMatrixMetadata(unittest.TestCase):
    def test_metadata_correct_case1(self):
        '''
        Typically, the metadata is collected following a successful
        validation.  Do that here
        '''
        m = Matrix()
        resource_path = os.path.join(TESTDIR, 'test_matrix.tsv')
        is_valid, err = m.validate_type(resource_path)
        self.assertTrue(is_valid)
        self.assertIsNone(err)

        # OK, the validation worked.  Get metadata
        metadata = m.extract_metadata(resource_path)

        # Parse the test file to ensure we extracted the right content.
        line = open(resource_path).readline()
        contents = line.strip().split('\t')
        samplenames = contents[1:]
        obs_list = [Observation(x) for x in samplenames]

        gene_list = []
        for i, line in enumerate(open(resource_path)):
            if i > 0:
                g = line.split('\t')[0]
                gene_list.append(g)
        feature_list = [Feature(x) for x in gene_list]

        obs_set = ObservationSetSerializer(ObservationSet(obs_list)).data
        feature_set = FeatureSetSerializer(FeatureSet(feature_list)).data

        self.assertEqual(obs_set, metadata['observation_set'])
        self.assertEqual(feature_set, metadata['feature_set'])
        self.assertIsNone(metadata['parent_operation'])

    def test_metadata_correct_case2(self):
        '''
        Typically, the metadata is collected following a successful
        validation.  However, here we don't validate.  Check that 
        it goes and collects the table in the process
        '''
        m = Matrix()
        resource_path = os.path.join(TESTDIR, 'test_matrix.tsv')
        metadata = m.extract_metadata(resource_path)

        # Parse the test file to ensure we extracted the right content.
        line = open(resource_path).readline()
        contents = line.strip().split('\t')
        samplenames = contents[1:]
        obs_list = [Observation(x) for x in samplenames]

        gene_list = []
        for i, line in enumerate(open(resource_path)):
            if i > 0:
                g = line.split('\t')[0]
                gene_list.append(g)
        feature_list = [Feature(x) for x in gene_list]

        obs_set = ObservationSetSerializer(ObservationSet(obs_list)).data
        feature_set = FeatureSetSerializer(FeatureSet(feature_list)).data

        self.assertEqual(obs_set, metadata['observation_set'])
        self.assertEqual(feature_set, metadata['feature_set'])
        self.assertIsNone(metadata['parent_operation'])

class TestIntegerMatrixMetadata(unittest.TestCase):
    def test_metadata_correct_case1(self):
        '''
        Typically, the metadata is collected following a successful
        validation.  Do that here
        '''
        m = IntegerMatrix()
        resource_path = os.path.join(TESTDIR, 'test_integer_matrix.tsv')
        is_valid, err = m.validate_type(resource_path)
        self.assertTrue(is_valid)
        self.assertIsNone(err)

        # OK, the validation worked.  Get metadata
        metadata = m.extract_metadata(resource_path)

        # Parse the test file to ensure we extracted the right content.
        line = open(resource_path).readline()
        contents = line.strip().split('\t')
        samplenames = contents[1:]
        obs_list = [Observation(x) for x in samplenames]

        gene_list = []
        for i, line in enumerate(open(resource_path)):
            if i > 0:
                g = line.split('\t')[0]
                gene_list.append(g)
        feature_list = [Feature(x) for x in gene_list]

        obs_set = ObservationSetSerializer(ObservationSet(obs_list)).data
        feature_set = FeatureSetSerializer(FeatureSet(feature_list)).data

        self.assertEqual(obs_set, metadata['observation_set'])
        self.assertEqual(feature_set, metadata['feature_set'])
        self.assertIsNone(metadata['parent_operation'])

    def test_metadata_correct_case2(self):
        '''
        Typically, the metadata is collected following a successful
        validation.  Do that here
        '''
        m = IntegerMatrix()
        resource_path = os.path.join(TESTDIR, 'test_integer_matrix.tsv')
        metadata = m.extract_metadata(resource_path)

        # Parse the test file to ensure we extracted the right content.
        line = open(resource_path).readline()
        contents = line.strip().split('\t')
        samplenames = contents[1:]
        obs_list = [Observation(x) for x in samplenames]

        gene_list = []
        for i, line in enumerate(open(resource_path)):
            if i > 0:
                g = line.split('\t')[0]
                gene_list.append(g)
        feature_list = [Feature(x) for x in gene_list]

        obs_set = ObservationSetSerializer(ObservationSet(obs_list)).data
        feature_set = FeatureSetSerializer(FeatureSet(feature_list)).data

        self.assertEqual(obs_set, metadata['observation_set'])
        self.assertEqual(feature_set, metadata['feature_set'])
        self.assertIsNone(metadata['parent_operation'])

class TestAnnotationTableMetadata(unittest.TestCase):

    def test_metadata_correct(self):
        resource_path = os.path.join(TESTDIR, 'three_column_annotation.tsv')
        t = AnnotationTable()
        column_dict = {}
        obs_list = []
        for i, line in enumerate(open(resource_path)):
            if i == 0:
                contents = line.strip().split('\t')
                for j,c in enumerate(contents[1:]):
                    column_dict[j] = c
            else:
                contents = line.strip().split('\t')
                samplename = contents[0]
                attr_dict = {}
                for j,v in enumerate(contents[1:]):
                    attr = StringAttribute(v)
                    attr_dict[column_dict[j]] = attr
                obs = Observation(samplename, attr_dict)
                obs_list.append(obs)
        expected_obs_set = ObservationSetSerializer(ObservationSet(obs_list)).data
        metadata = t.extract_metadata(resource_path)
        self.assertEqual(metadata['observation_set'], expected_obs_set)
        self.assertIsNone(metadata['feature_set'])
        self.assertIsNone(metadata['parent_operation'])


class TestFeatureTableMetadata(unittest.TestCase):

    def test_metadata_correct(self):
        resource_path = os.path.join(TESTDIR, 'gene_annotations.tsv')
        t = FeatureTable()
        column_dict = {}
        feature_list = []
        for i, line in enumerate(open(resource_path)):
            if i == 0:
                contents = line.strip().split('\t')
                for j,c in enumerate(contents[1:]):
                    column_dict[j] = c
            else:
                contents = line.strip().split('\t')
                gene_name = contents[0]
                attr_dict = {}
                for j,v in enumerate(contents[1:]):
                    try:
                        v = int(v)
                        attr = IntegerAttribute(v)
                    except ValueError:
                        attr = StringAttribute(v)

                    attr_dict[column_dict[j]] = attr
                f = Feature(gene_name, attr_dict)
                feature_list.append(f)
        expected_feature_set = FeatureSetSerializer(FeatureSet(feature_list)).data
        metadata = t.extract_metadata(resource_path)
        self.assertEqual(metadata['feature_set'], expected_feature_set)
        self.assertIsNone(metadata['observation_set'])
        self.assertIsNone(metadata['parent_operation'])


class TestBedFileMetadata(unittest.TestCase):

    def test_metadata_correct(self):
        resource_path = os.path.join(TESTDIR, 'example_bed.bed')
        bf = BEDFile()
        metadata = bf.extract_metadata(resource_path)
        self.assertIsNone(metadata['feature_set'])
        self.assertIsNone(metadata['observation_set'])
        self.assertIsNone(metadata['parent_operation'])
