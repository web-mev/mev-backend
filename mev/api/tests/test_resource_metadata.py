import unittest
import unittest.mock as mock
import os
import uuid
import numpy as np
import pandas as pd
import copy

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

from api.serializers.resource_metadata import ResourceMetadataSerializer, \
    ResourceMetadataObservationsSerializer, \
    ResourceMetadataFeaturesSerializer, \
    ResourceMetadataParentOperationSerializer
from api.serializers.observation import ObservationSerializer
from api.serializers.feature import FeatureSerializer
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
from resource_types import PARENT_OP_KEY, \
    OBSERVATION_SET_KEY, \
    FEATURE_SET_KEY, \
    RESOURCE_KEY
from api.tests.base import BaseAPITestCase
from api.utilities.resource_utilities import add_metadata_to_resource

# the api/tests dir
TESTDIR = os.path.dirname(__file__)
TESTDIR = os.path.join(TESTDIR, 'resource_validation_test_files')

def create_observation_set():
    # create a couple Observations to use and a corresponding serializer
    el1 = Observation('sampleA', {
        'phenotype': StringAttribute('WT')
    })
    el1_serializer = ObservationSerializer(el1)

    el2 = Observation('sampleB', {
        'phenotype': StringAttribute('KO')
    })
    el2_serializer = ObservationSerializer(el2)

    # the correct serialized representation of an ElementSet instance
    observation_set_data = {
        'multiple': True,
        'elements': [
            el1_serializer.data,
            el2_serializer.data
        ]
    }
    return observation_set_data

def create_feature_set():
    # create a couple Features to use and a corresponding serializer
    el1 = Feature('featureA', {
        'pathway': StringAttribute('foo')
    })
    el1_serializer = FeatureSerializer(el1)

    el2 = Feature('sampleB', {
        'pathway': StringAttribute('bar')
    })
    el2_serializer = FeatureSerializer(el2)

    # the correct serialized representation of an ElementSet instance
    feature_set_data = {
        'multiple': True,
        'elements': [
            el1_serializer.data,
            el2_serializer.data
        ]
    }
    return feature_set_data

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

    def prepare_metadata(self):
        '''
        This is a helper function which creates a new Resource and associates
        some mock metadata with it. Used by multiple testing functions.
        '''
        new_resource = Resource.objects.create(
            name = 'foo.txt',
            owner = self.regular_user_1,
            is_active=True
        )
        self.new_resource_pk = new_resource.pk

        self.expected_observation_set = create_observation_set()
        self.expected_feature_set = create_feature_set()
        self.expected_parent_operation = None
        metadata = {
            RESOURCE_KEY: self.new_resource_pk,
            OBSERVATION_SET_KEY: copy.deepcopy(self.expected_observation_set),
            FEATURE_SET_KEY: copy.deepcopy(self.expected_feature_set),
            PARENT_OP_KEY: self.expected_parent_operation
        }
        rms = ResourceMetadataSerializer(data=metadata)
        if rms.is_valid(raise_exception=True):
            rms.save()


    def test_retrieve_full_metadata(self):
        '''
        Test that we retrieve the proper metadata from a request to the 
        endpoint for the full metadata object
        '''
        self.prepare_metadata()
        url = reverse(
            'resource-metadata-detail', 
            kwargs={'pk':self.new_resource_pk}
        )
        response = self.authenticated_regular_client.get(url)
        response_json = response.json()
        obs_set = response_json[OBSERVATION_SET_KEY]
        elements = obs_set['elements']
        self.assertCountEqual(elements, self.expected_observation_set['elements'])
        fs = response_json[FEATURE_SET_KEY]
        elements = fs['elements']
        self.assertCountEqual(elements, self.expected_feature_set['elements'])
        self.assertEqual(response_json[PARENT_OP_KEY], self.expected_parent_operation)

    def test_retrieve_observation_metadata(self):
        '''
        Test that we retrieve the proper metadata from a request to 
        get only the observations from the full metadata
        '''
        self.prepare_metadata()
        url = reverse(
            'resource-metadata-observations', 
            kwargs={'pk':self.new_resource_pk}
        )
        response = self.authenticated_regular_client.get(url)
        response_json = response.json()
        response_keys = response_json.keys()
        self.assertTrue(len(response_keys) == 1)
        self.assertTrue(list(response_keys)[0] == OBSERVATION_SET_KEY)
        obs_set = response_json[OBSERVATION_SET_KEY]
        elements = obs_set['elements']
        self.assertCountEqual(elements, self.expected_observation_set['elements'])

    def test_retrieve_feature_metadata(self):
        '''
        Test that we retrieve the proper metadata from a request to 
        get only the features from the full metadata
        '''
        self.prepare_metadata()
        url = reverse(
            'resource-metadata-features', 
            kwargs={'pk':self.new_resource_pk}
        )
        response = self.authenticated_regular_client.get(url)
        response_json = response.json()
        response_keys = response_json.keys()
        self.assertTrue(len(response_keys) == 1)
        self.assertTrue(list(response_keys)[0] == FEATURE_SET_KEY)
        fs = response_json[FEATURE_SET_KEY]
        elements = fs['elements']
        self.assertCountEqual(elements, self.expected_feature_set['elements'])

    def test_retrieve_parent_operation_metadata(self):
        '''
        Test that we retrieve the proper metadata from a request to 
        get only the parent_operation from the full metadata
        '''
        self.prepare_metadata()
        url = reverse(
            'resource-metadata-parent-operation', 
            kwargs={'pk':self.new_resource_pk}
        )
        response = self.authenticated_regular_client.get(url)
        response_json = response.json()
        response_keys = response_json.keys()
        self.assertTrue(len(response_keys) == 1)
        self.assertTrue(list(response_keys)[0] == PARENT_OP_KEY)
        self.assertEqual(response_json[PARENT_OP_KEY], self.expected_parent_operation)

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
        # Commented out when removed the feature metadata, as it was causing database
        # issues due to the size of the json object.
        #self.assertEqual(feature_set, metadata[FEATURE_SET_KEY])
        self.assertIsNone( metadata[FEATURE_SET_KEY])
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
        # Commented out when removed the feature metadata, as it was causing database
        # issues due to the size of the json object.
        #self.assertEqual(feature_set, metadata[FEATURE_SET_KEY])
        self.assertIsNone( metadata[FEATURE_SET_KEY])
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
        # Commented out when removed the feature metadata, as it was causing database
        # issues due to the size of the json object.
        #self.assertEqual(feature_set, metadata[FEATURE_SET_KEY])
        self.assertIsNone( metadata[FEATURE_SET_KEY])
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
        # Commented out when removed the feature metadata, as it was causing database
        # issues due to the size of the json object.
        #self.assertEqual(feature_set, metadata[FEATURE_SET_KEY])
        self.assertIsNone( metadata[FEATURE_SET_KEY])
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


class TestFeatureTableMetadata(BaseAPITestCase):

    def setUp(self):
        self.establish_clients()

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
        # Commented out when we removed the automatic creation of Feature metadata
        # for FeatureTable resource types. For large files, it was causing issues
        # with exceptionally large JSON failing to store in db table.
        #self.assertEqual(metadata[FEATURE_SET_KEY], expected_feature_set)
        self.assertIsNone(metadata[FEATURE_SET_KEY])
        self.assertIsNone(metadata[OBSERVATION_SET_KEY])
        self.assertIsNone(metadata[PARENT_OP_KEY])

    def test_serialization_works(self):
        '''
        Test that serialization works as expected by using the metadata method
        Needs to be able to serialize tables that have na and inf values.
        '''
        columns = ['colA', 'colB', 'colC']
        rows = ['geneA', 'geneB', 'geneC']
        values = np.arange(9).reshape((3,3))
        df = pd.DataFrame(values, index=rows, columns=columns)
        df.loc['geneA', 'colB'] = np.inf
        df.loc['geneB', 'colA'] = np.nan
        path = '/tmp/test_matrix.tsv'
        df.to_csv(path, sep='\t')

        ft = FeatureTable()
        m =  ft.extract_metadata(path)
        r = Resource.objects.all()[0]
        m[RESOURCE_KEY] = r.pk
        rms = ResourceMetadataSerializer(data=m)
        self.assertTrue(rms.is_valid(raise_exception=True))

    def test_dge_output_with_na(self):
        '''
        This tests that the metadata extraction handles the case where
        there are nan/NaN among the covariates in a FeatureTable
        '''
        # this file has a row with nan for some of the values; a p-value was not called
        resource_path = os.path.join(TESTDIR, 'deseq_results_example.tsv')
        self.assertTrue(os.path.exists(resource_path))
        t = FeatureTable()
        metadata = t.extract_metadata(resource_path)
        r = Resource.objects.filter(owner=self.regular_user_1, is_active=True)[0]
        add_metadata_to_resource(r, metadata)

        url = reverse(
            'resource-metadata-detail', 
            kwargs={'pk':r.pk}
        )
        response = self.authenticated_regular_client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_dge_concat_output_with_na(self):
        '''
        This tests that the metadata extraction handles the case where
        there are nan/NaN among the covariates in a FeatureTable
        '''
        # this file has a row with nan for some of the values; a p-value was not called
        resource_path = os.path.join(TESTDIR, 'deseq_results_example_concat.tsv')
        self.assertTrue(os.path.exists(resource_path))
        t = FeatureTable()
        metadata = t.extract_metadata(resource_path)
        r = Resource.objects.filter(owner=self.regular_user_1, is_active=True)[0]
        add_metadata_to_resource(r, metadata)
        rmm = ResourceMetadata.objects.get(resource=r)

        url = reverse(
            'resource-metadata-detail', 
            kwargs={'pk':r.pk}
        )
        response = self.authenticated_regular_client.get(url)
        self.assertEqual(response.status_code, 200)
        j = response.json()


class TestBedFileMetadata(unittest.TestCase):

    def test_metadata_correct(self):
        resource_path = os.path.join(TESTDIR, 'example_bed.bed')
        bf = BEDFile()
        metadata = bf.extract_metadata(resource_path)
        self.assertIsNone(metadata[FEATURE_SET_KEY])
        self.assertIsNone(metadata[OBSERVATION_SET_KEY])
        self.assertIsNone(metadata[PARENT_OP_KEY])


class TestResourceMetadataSerializer(BaseAPITestCase):

    def test_good_obs_set(self):
        '''
        Tests that good observation sets are accepted when creating
        ResourceMetadata
        '''
        r = Resource.objects.all()
        r = r[0]
        # the bad obs set is missing the `elements` key
        good_obs_set = {
            'multiple': True,
            'elements':[
                {
                    'id': 'foo'
                },
                {
                    'id': 'bar'
                }
            ]
        }
        d = {
            RESOURCE_KEY: r.pk,
            OBSERVATION_SET_KEY: good_obs_set,
            FEATURE_SET_KEY: None,
            PARENT_OP_KEY:None
        }
        rms = ResourceMetadataSerializer(data=d)
        self.assertTrue(rms.is_valid())

    def test_bad_obs_set(self):
        '''
        Tests that bad observation sets are rejected when creating
        ResourceMetadata
        '''
        r = Resource.objects.all()
        r = r[0]
        # the bad obs set is missing the `elements` key
        bad_obs_set = {
            'multiple': True
        }
        d = {
            RESOURCE_KEY: r.pk,
            OBSERVATION_SET_KEY: bad_obs_set,
            FEATURE_SET_KEY: None,
            PARENT_OP_KEY:None
        }
        rms = ResourceMetadataSerializer(data=d)
        self.assertFalse(rms.is_valid())

        bad_obs_set = {}
        d = {
            RESOURCE_KEY: r.pk,
            OBSERVATION_SET_KEY: bad_obs_set,
            FEATURE_SET_KEY: None,
            PARENT_OP_KEY:None
        }
        rms = ResourceMetadataSerializer(data=d)
        self.assertFalse(rms.is_valid())

        bad_obs_set = {
            'multiple': True,
            'elements':[
                {
                    'id': 'foo'
                },
                {
                    'id': 'foo' # a duplicated key
                }
            ]
        }        
        d = {
            RESOURCE_KEY: r.pk,
            OBSERVATION_SET_KEY: bad_obs_set,
            FEATURE_SET_KEY: None,
            PARENT_OP_KEY:None
        }
        rms = ResourceMetadataSerializer(data=d)
        self.assertFalse(rms.is_valid())

    def test_good_feature_set(self):
        '''
        Tests that good featire sets are accepted when creating
        ResourceMetadata
        '''
        r = Resource.objects.all()
        r = r[0]
        # the bad obs set is missing the `elements` key
        good_feature_set = {
            'multiple': True,
            'elements':[
                {
                    'id': 'foo'
                },
                {
                    'id': 'bar'
                }
            ]
        }
        d = {
            RESOURCE_KEY: r.pk,
            OBSERVATION_SET_KEY: None,
            FEATURE_SET_KEY: good_feature_set,
            PARENT_OP_KEY:None
        }
        rms = ResourceMetadataSerializer(data=d)
        self.assertTrue(rms.is_valid())

    def test_bad_feature_set(self):
        '''
        Tests that bad feature sets are rejected when creating
        ResourceMetadata
        '''
        r = Resource.objects.all()
        r = r[0]
        # the bad obs set is missing the `elements` key
        bad_feature_set = {
            'multiple': True
        }
        d = {
            RESOURCE_KEY: r.pk,
            OBSERVATION_SET_KEY: bad_feature_set,
            FEATURE_SET_KEY: None,
            PARENT_OP_KEY:None
        }
        rms = ResourceMetadataSerializer(data=d)
        self.assertFalse(rms.is_valid())

        bad_feature_set = {}
        d = {
            RESOURCE_KEY: r.pk,
            OBSERVATION_SET_KEY: None,
            FEATURE_SET_KEY: bad_feature_set,
            PARENT_OP_KEY:None
        }
        rms = ResourceMetadataSerializer(data=d)
        self.assertFalse(rms.is_valid())

        bad_feature_set = {
            'multiple': True,
            'elements':[
                {
                    'id': 'foo'
                },
                {
                    'id': 'foo' # a duplicated key
                }
            ]
        }        
        d = {
            RESOURCE_KEY: r.pk,
            OBSERVATION_SET_KEY: None,
            FEATURE_SET_KEY: bad_feature_set,
            PARENT_OP_KEY:None
        }
        rms = ResourceMetadataSerializer(data=d)
        self.assertFalse(rms.is_valid())

    def test_missing_keys_in_resource_metadata(self):
        '''
        Tests
        '''
        # can't have a null resource key-- NEEDS to be assoc.
        # with a resource
        d = {
            RESOURCE_KEY: None,
            OBSERVATION_SET_KEY: None,
            FEATURE_SET_KEY: None,
            PARENT_OP_KEY:None
        }
        rms = ResourceMetadataSerializer(data=d)
        self.assertFalse(rms.is_valid())

        r = Resource.objects.all()
        r = r[0]

        # delete any existing metadata on this resource (in case it's there
        # from a prior test)
        rr = ResourceMetadata.objects.filter(resource=r)
        if len(rr) == 1:
             rr.delete()
        d = {
            RESOURCE_KEY: r.pk,
            OBSERVATION_SET_KEY: None,
            FEATURE_SET_KEY: None,
            PARENT_OP_KEY:None
        }
        rms = ResourceMetadataSerializer(data=d)
        self.assertTrue(rms.is_valid())
        rm = rms.save()
        self.assertIsNone(rm.observation_set)
        self.assertIsNone(rm.feature_set)
        self.assertIsNone(rm.parent_operation)

        # it's OK to only have the resource key.
        # The others are set to null by default.
        d = {
            RESOURCE_KEY: r.pk,
        }
        # delete any existing metadata on this resource (in case it's there
        # from a prior test)
        rr = ResourceMetadata.objects.filter(resource=r)
        if len(rr) == 1:
             rr.delete()
        rms = ResourceMetadataSerializer(data=d)
        self.assertTrue(rms.is_valid())
        rm = rms.save()
        self.assertIsNone(rm.observation_set)
        self.assertIsNone(rm.feature_set)
        self.assertIsNone(rm.parent_operation)