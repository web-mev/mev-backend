import unittest
import unittest.mock as mock
import os
import uuid

from django.urls import reverse
from django.core.exceptions import ImproperlyConfigured
from rest_framework import status


from api.models import Resource, ResourceMetadata

from api.data_structures import Observation, \
    ObservationSet, \
    Feature, \
    FeatureSet, \
    StringAttribute, \
    IntegerAttribute

from api.serializers.observation_set import ObservationSetSerializer
from api.serializers.feature_set import FeatureSetSerializer
from resource_types import OBSERVATION_SET_KEY, \
    FEATURE_SET_KEY, \
    RESOURCE_KEY, \
    PARENT_OP_KEY
from resource_types.table_types import TableResource, \
    Matrix, \
    IntegerMatrix, \
    AnnotationTable, \
    FeatureTable, \
    BEDFile
from api.tests.base import BaseAPITestCase

# the api/tests dir
TESTDIR = os.path.dirname(__file__)
TESTDIR = os.path.join(TESTDIR, 'resource_validation_test_files')

class TestRetrieveResourceMetadata(BaseAPITestCase):

    def setUp(self):
        self.establish_clients()

    def test_retrieve_zero_assoc_metadata_gives_404(self):
        '''
        If a Resource has no metdata (as is the case before it has
        been validated), it should return a 404.

        When validation is happening, the resource is inactive
        and we should not get any results (mainly b/c they could
        change following any validation, etc.)
        '''
        inactive_resources = Resource.objects.filter(
            is_active=False, owner=self.regular_user_1)
        if len(inactive_resources) == 0:
            raise ImproperlyConfigured('Need at least one inactive '
                'Resource to run this test')
        r = inactive_resources[0]

        # check that there was, in fact, metadata for this
        # resource.  
        rm = ResourceMetadata.objects.filter(resource=r)
        self.assertTrue(len(rm) == 1)

        pk = r.pk
        url = reverse(
            'resource-metadata-detail', 
            kwargs={'pk':pk}
        )
        response = self.authenticated_regular_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_resource_without_type_returns_404_for_metadata(self):
        '''
        Until a type has been successfully validated, any requests for the metadata
        associated with the Resource should return a 404
        '''
        unset_resources = Resource.objects.filter(
            is_active=True, 
            owner=self.regular_user_1).exclude(resource_type__isnull=False)
        if len(unset_resources) == 0:
            raise ImproperlyConfigured('Need at least one active Resource without '
                'a type to run this test')
        r = unset_resources[0]
        pk = r.pk
        url = reverse(
            'resource-metadata-detail', 
            kwargs={'pk':pk}
        )
        response = self.authenticated_regular_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_missing_resource_metadata(self):
        '''
        Here, although the case shouldn't happen (since validated
        resources are assigned metadata),
        we check that a Resource without any associated
        metadata returns a 404
        '''
        new_resource = Resource.objects.create(
            name = 'foo.txt',
            owner = self.regular_user_1
        )
        pk = new_resource.pk
        url = reverse(
            'resource-metadata-detail', 
            kwargs={'pk':pk}
        )
        response = self.authenticated_regular_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_resource_metadata_for_nonexistent_resource(self):
        '''
        Check that a bad UUID (that of a resource that does not exist)
        fails the request
        '''
        url = reverse(
            'resource-metadata-detail', 
            kwargs={'pk':uuid.uuid4()}
        )
        response = self.authenticated_regular_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @mock.patch('api.views.resource_metadata.ResourceMetadataView.get_queryset')
    def test_resource_with_multiple_metadata_causes_error(self, mock_get_queryset):
        '''
        If a Resource has multiple metdata instances associated with it,
        issue an error.  Generally this should not happen as we block
        any attempts to create many-to-one associations.
        '''
        active_resources = Resource.objects.filter(
            is_active=True, 
            owner=self.regular_user_1).exclude(resource_type__isnull=True)
        if len(active_resources) == 0:
            raise ImproperlyConfigured('Need at least one active '
                'Resource to run this test')
        r = active_resources[0]

        mock_get_queryset.return_value = [0,1]
        url = reverse(
            'resource-metadata-detail', 
            kwargs={'pk':r.pk}
        )
        response = self.authenticated_regular_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)



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

        self.assertEqual(obs_set, metadata[OBSERVATION_SET_KEY])
        self.assertEqual(feature_set, metadata[FEATURE_SET_KEY])
        self.assertIsNone(metadata[PARENT_OP_KEY])

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

        self.assertEqual(obs_set, metadata[OBSERVATION_SET_KEY])
        self.assertEqual(feature_set, metadata[FEATURE_SET_KEY])
        self.assertIsNone(metadata[PARENT_OP_KEY])

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

        self.assertEqual(obs_set, metadata[OBSERVATION_SET_KEY])
        self.assertEqual(feature_set, metadata[FEATURE_SET_KEY])
        self.assertIsNone(metadata[PARENT_OP_KEY])

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

        self.assertEqual(obs_set, metadata[OBSERVATION_SET_KEY])
        self.assertEqual(feature_set, metadata[FEATURE_SET_KEY])
        self.assertIsNone(metadata[PARENT_OP_KEY])

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
        self.assertEqual(metadata[OBSERVATION_SET_KEY], expected_obs_set)
        self.assertIsNone(metadata[FEATURE_SET_KEY])
        self.assertIsNone(metadata[PARENT_OP_KEY])


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
        self.assertEqual(metadata[FEATURE_SET_KEY], expected_feature_set)
        self.assertIsNone(metadata[OBSERVATION_SET_KEY])
        self.assertIsNone(metadata[PARENT_OP_KEY])


class TestBedFileMetadata(unittest.TestCase):

    def test_metadata_correct(self):
        resource_path = os.path.join(TESTDIR, 'example_bed.bed')
        bf = BEDFile()
        metadata = bf.extract_metadata(resource_path)
        self.assertIsNone(metadata[FEATURE_SET_KEY])
        self.assertIsNone(metadata[OBSERVATION_SET_KEY])
        self.assertIsNone(metadata[PARENT_OP_KEY])
