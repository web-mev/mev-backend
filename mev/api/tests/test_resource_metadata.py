from io import BytesIO
import unittest
import unittest.mock as mock
import os
import uuid
import numpy as np
import pandas as pd
import copy

from django.urls import reverse
from django.core.exceptions import ImproperlyConfigured
from django.core.files import File
from rest_framework import status
from rest_framework.serializers import ValidationError

from api.models import Resource, ResourceMetadata

from data_structures.observation_set import ObservationSet
from data_structures.feature_set import FeatureSet
from data_structures.attribute_types import StringAttribute, \
    UnrestrictedStringAttribute, \
    IntegerAttribute

from api.serializers.resource_metadata import ResourceMetadataSerializer
from api.models import WorkspaceExecutedOperation, \
    ExecutedOperation, \
    Workspace, \
    Operation as OperationDb

from resource_types.table_types import TableResource, \
    Matrix, \
    IntegerMatrix, \
    AnnotationTable, \
    FeatureTable, \
    BED3File
from constants import PARENT_OP_KEY, \
    OBSERVATION_SET_KEY, \
    FEATURE_SET_KEY, \
    RESOURCE_KEY, \
    TSV_FORMAT
from api.tests.base import BaseAPITestCase
from api.utilities.resource_utilities import add_metadata_to_resource
from api.tests.test_helpers import associate_file_with_resource

# the api/tests dir
TESTDIR = os.path.dirname(__file__)
TESTDIR = os.path.join(TESTDIR, 'resource_validation_test_files')

def create_observation_set():
    # create a couple Observations to use and a corresponding serializer
    el1 = {
        'id':'sampleA', 
        'attributes': {
            'phenotype': {
                'attribute_type': 'String',
                'value': 'WT'
            }
        }
    }

    el2 = {
        'id':'sampleB', 
        'attributes': {
            'phenotype': {
                'attribute_type': 'String',
                'value': 'KO'
            }
        }
    }

    obs_set = ObservationSet(
        {
            'elements': [
                el1,
                el2
            ]
        }
    )
    return obs_set.to_simple_dict()

def create_feature_set():

    f1 = {
        'id':'featureA', 
        'attributes': {
            'pathway': {
                'attribute_type': 'String',
                'value': 'foo'
            }
        }
    }

    f2 = {
        'id':'featureB', 
        'attributes': {
            'pathway': {
                'attribute_type': 'String',
                'value': 'bar'
            }
        }
    }

    fset = FeatureSet(
        {
            'elements': [
                f1,
                f2
            ]
        }
    )
    return fset.to_simple_dict()


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

        usable_records = []
        for r in inactive_resources:
            rm = ResourceMetadata.objects.filter(resource=r)
            if len(rm) == 1:
                usable_records.append(r)

        if len(usable_records) == 0:
            raise ImproperlyConfigured('Need at least one inactive '
                'Resource with associated metadata to run this test')

        r = usable_records[0]

        # double-check that there was, in fact, metadata for this
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
            owner = self.regular_user_1,
            datafile=File(BytesIO(), 'somefile')
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
            is_active=True,
            datafile=File(BytesIO(), 'somefile')
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

class TestMatrixMetadata(BaseAPITestCase):

    def setUp(self):
        self.establish_clients()

    def test_metadata_correct_case1(self):
        '''
        Typically, the metadata is collected following a successful
        validation.  Do that here
        '''
        m = Matrix()
        resource_path = os.path.join(TESTDIR, 'test_matrix.tsv')
        r = Resource.objects.filter(owner=self.regular_user_1, is_active=True)[0]
        associate_file_with_resource(r, resource_path)
        is_valid, err = m.validate_type(r, 'tsv')
        self.assertTrue(is_valid)
        self.assertIsNone(err)

        # OK, the validation worked.  Get metadata
        metadata = m.extract_metadata(r)

        # Parse the test file to ensure we extracted the right content.
        line = open(resource_path).readline()
        contents = line.strip().split('\t')
        samplenames = contents[1:]
        obs_list = [{'id':x} for x in samplenames]

        gene_list = []
        for i, line in enumerate(open(resource_path)):
            if i > 0:
                g = line.split('\t')[0]
                gene_list.append(g)
        feature_list = [{'id':x} for x in gene_list]

        obs_set = ObservationSet({'elements': obs_list}).to_simple_dict()
        feature_set = FeatureSet({'elements': feature_list}).to_simple_dict()

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
        r = Resource.objects.filter(owner=self.regular_user_1, is_active=True)[0]
        associate_file_with_resource(r, resource_path)
        metadata = m.extract_metadata(r)

        # Parse the test file to ensure we extracted the right content.
        line = open(resource_path).readline()
        contents = line.strip().split('\t')
        samplenames = contents[1:]
        obs_list = [{'id': x}  for x in samplenames]

        gene_list = []
        for i, line in enumerate(open(resource_path)):
            if i > 0:
                g = line.split('\t')[0]
                gene_list.append(g)
        feature_list = [{'id': x} for x in gene_list]

        obs_set = ObservationSet({'elements': obs_list}).to_simple_dict()
        feature_set = FeatureSet({'elements': feature_list}).to_simple_dict()

        self.assertEqual(obs_set, metadata[OBSERVATION_SET_KEY])
        # Commented out when removed the feature metadata, as it was causing database
        # issues due to the size of the json object.
        #self.assertEqual(feature_set, metadata[FEATURE_SET_KEY])
        self.assertIsNone( metadata[FEATURE_SET_KEY])
        self.assertIsNone(metadata[PARENT_OP_KEY])

        
class TestIntegerMatrixMetadata(BaseAPITestCase):

    def setUp(self):
        self.establish_clients()

    def test_metadata_correct_case1(self):
        '''
        Typically, the metadata is collected following a successful
        validation.  Do that here
        '''
        m = IntegerMatrix()
        resource_path = os.path.join(TESTDIR, 'test_integer_matrix.tsv')
        r = Resource.objects.filter(owner=self.regular_user_1, is_active=True)[0]
        associate_file_with_resource(r, resource_path)
        is_valid, err = m.validate_type(r, 'tsv')

        self.assertTrue(is_valid)
        self.assertIsNone(err)

        # OK, the validation worked.  Get metadata
        metadata = m.extract_metadata(r)

        # Parse the test file to ensure we extracted the right content.
        line = open(resource_path).readline()
        contents = line.strip().split('\t')
        samplenames = contents[1:]
        obs_list = [{'id': x} for x in samplenames]

        obs_set = ObservationSet(
            {
                'elements': obs_list
            }
        )
        self.assertDictEqual(obs_set.to_simple_dict(), metadata[OBSERVATION_SET_KEY])
        self.assertIsNone( metadata[FEATURE_SET_KEY])
        self.assertIsNone(metadata[PARENT_OP_KEY])

    def test_metadata_correct_case2(self):
        '''
        Typically, the metadata is collected following a successful
        validation.  Do that here
        '''
        m = IntegerMatrix()
        resource_path = os.path.join(TESTDIR, 'test_integer_matrix.tsv')
        r = Resource.objects.filter(owner=self.regular_user_1, is_active=True)[0]
        associate_file_with_resource(r, resource_path)
        metadata = m.extract_metadata(r)

        # Parse the test file to ensure we extracted the right content.
        line = open(resource_path).readline()
        contents = line.strip().split('\t')
        samplenames = contents[1:]
        obs_list = [{'id': x} for x in samplenames]

        gene_list = []
        for i, line in enumerate(open(resource_path)):
            if i > 0:
                g = line.split('\t')[0]
                gene_list.append(g)
        feature_list = [{'id': x} for x in gene_list]

        obs_set = ObservationSet({'elements': obs_list}).to_simple_dict()
        feature_set = FeatureSet({'elements': feature_list}).to_simple_dict()

        self.assertEqual(obs_set, metadata[OBSERVATION_SET_KEY])
        # Commented out when removed the feature metadata, as it was causing database
        # issues due to the size of the json object.
        #self.assertEqual(feature_set, metadata[FEATURE_SET_KEY])
        self.assertIsNone( metadata[FEATURE_SET_KEY])
        self.assertIsNone(metadata[PARENT_OP_KEY])
       

class TestAnnotationTableMetadata(BaseAPITestCase):

    def setUp(self):
        self.establish_clients()

    def test_metadata_handles_type_conversion(self):
        '''
        Note that annotation/element tables can have
        columns that are incorrectly handled due to
        pandas conversion issues.  See
        https://github.com/pandas-dev/pandas/issues/12859
        '''
        resource_path = os.path.join(TESTDIR, 'test_ann_with_int_column.tsv')
        r = Resource.objects.filter(owner=self.regular_user_1, is_active=True)[0]
        associate_file_with_resource(r, resource_path)
        t = AnnotationTable()
        meta = t.extract_metadata(r)
        expected_results = [1,2]
        actual_results = []
        for x in meta['observation_set']['elements']:
            attr = x['attributes']
            actual_results.append(attr['int_col']['value'])
        self.assertCountEqual(expected_results, actual_results)
        

    def test_metadata_correct(self):
        resource_path = os.path.join(TESTDIR, 'three_column_annotation.tsv')
        r = Resource.objects.filter(owner=self.regular_user_1, is_active=True)[0]
        associate_file_with_resource(r, resource_path)
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
                    attr = UnrestrictedStringAttribute(v)
                    attr_dict[column_dict[j]] = attr.to_dict()
                obs = {'id': samplename, 'attributes': attr_dict}
                obs_list.append(obs)
        expected_obs_set = ObservationSet(
            {'elements': obs_list}
        ).to_simple_dict()
        metadata = t.extract_metadata(r)
        self.assertEqual(metadata[OBSERVATION_SET_KEY], expected_obs_set)
        self.assertIsNone(metadata[FEATURE_SET_KEY])
        self.assertIsNone(metadata[PARENT_OP_KEY])
        
    def test_annotations_with_empty_fields_ok(self):
        '''
        Some of the fields in the annotation file don't have entries. Verify
        that this is acceptable.
        '''
        resource_path = os.path.join(TESTDIR, 'gbm.tsv')
        r = Resource.objects.filter(owner=self.regular_user_1, is_active=True)[0]
        associate_file_with_resource(r, resource_path)
        t = AnnotationTable()
        metadata = t.extract_metadata(r)
        add_metadata_to_resource(r, metadata)
    

class TestFeatureTableMetadata(BaseAPITestCase):

    def setUp(self):
        self.establish_clients()

    def test_metadata_correct(self):
        resource_path = os.path.join(TESTDIR, 'gene_annotations.tsv')
        r = Resource.objects.filter(owner=self.regular_user_1, is_active=True)[0]
        associate_file_with_resource(r, resource_path)
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

                    attr_dict[column_dict[j]] = attr.to_dict()
                f = {'id': gene_name, 'attributes': attr_dict}
                feature_list.append(f)
        expected_feature_set = FeatureSet({'elements': feature_list})
        metadata = t.extract_metadata(r)
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
        # now associate that file with a resource
        r = Resource.objects.filter(owner=self.regular_user_1, is_active=True)[0]
        associate_file_with_resource(r, path)

        ft = FeatureTable()
        m =  ft.extract_metadata(r)
        m[RESOURCE_KEY] = r.pk
        rms = ResourceMetadataSerializer(data=m)
        self.assertTrue(rms.is_valid(raise_exception=True))
        
        os.remove(path)

    def test_dge_output_with_na(self):
        '''
        This tests that the metadata extraction handles the case where
        there are nan/NaN among the covariates in a FeatureTable
        '''
        # this file has a row with nan for some of the values; a p-value was not called
        resource_path = os.path.join(TESTDIR, 'deseq_results_example.tsv')
        self.assertTrue(os.path.exists(resource_path))
        r = Resource.objects.filter(owner=self.regular_user_1, is_active=True)[0]
        associate_file_with_resource(r, resource_path)
        t = FeatureTable()
        metadata = t.extract_metadata(r)
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
        r = Resource.objects.filter(owner=self.regular_user_1, is_active=True)[0]
        resource_path = os.path.join(TESTDIR, 'deseq_results_example_concat.tsv')
        self.assertTrue(os.path.exists(resource_path))
        associate_file_with_resource(r, resource_path)
        t = FeatureTable()
        metadata = t.extract_metadata(r)
        add_metadata_to_resource(r, metadata)
        rmm = ResourceMetadata.objects.get(resource=r)

        url = reverse(
            'resource-metadata-detail', 
            kwargs={'pk':r.pk}
        )
        response = self.authenticated_regular_client.get(url)
        self.assertEqual(response.status_code, 200)
        j = response.json()
        

class TestBedFileMetadata(BaseAPITestCase):

    def setUp(self):
        self.establish_clients()

    def test_metadata_correct(self):
        resource_path = os.path.join(TESTDIR, 'example_bed.bed')
        r = Resource.objects.filter(owner=self.regular_user_1, is_active=True)[0]
        associate_file_with_resource(r, resource_path)
        bf = BED3File()
        metadata = bf.extract_metadata(r)
        self.assertIsNone(metadata[FEATURE_SET_KEY])
        self.assertIsNone(metadata[OBSERVATION_SET_KEY])
        self.assertIsNone(metadata[PARENT_OP_KEY])
        

class TestResourceMetadataSerializer(BaseAPITestCase):

    def setUp(self):
        self.establish_clients()

    def test_good_obs_set(self):
        '''
        Tests that good observation sets are accepted when creating
        ResourceMetadata
        '''
        r = Resource.objects.all()
        r = r[0]
        # the bad obs set is missing the `elements` key
        good_obs_set = {
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
        self.assertTrue(rms.is_valid(raise_exception=True))

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

        long_name = 'x'*200
        bad_obs_set = {
            'multiple': True,
            'elements':[
                {
                    'id': 'foo'
                },
                {
                    'id': long_name # the name is too long
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
        with self.assertRaisesRegex(ValidationError, long_name) as ex:
            rms.is_valid(raise_exception=True)

    def test_good_feature_set(self):
        '''
        Tests that good featire sets are accepted when creating
        ResourceMetadata
        '''
        r = Resource.objects.all()
        r = r[0]
        # the bad obs set is missing the `elements` key
        good_feature_set = {
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
        self.assertTrue(rms.is_valid(raise_exception=True))

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

        long_name = 'x'*200
        bad_feature_set = {
            'elements':[
                {
                    'id': 'foo'
                },
                {
                    'id': long_name # the name is too long
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
        with self.assertRaisesRegex(ValidationError, long_name) as ex:
            rms.is_valid(raise_exception=True)

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
        self.assertTrue(rms.is_valid(raise_exception=True))
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
        rms.is_valid(raise_exception=True)
        self.assertTrue(rms.is_valid())
        rm = rms.save()
        self.assertIsNone(rm.observation_set)
        self.assertIsNone(rm.feature_set)
        self.assertIsNone(rm.parent_operation)

    def test_parent_op_validation(self):
        '''
        Test that providing the UUID referencing a
        ExecutedOperation leads to a proper lookup
        of the instance.
        '''

        ops = OperationDb.objects.all()
        if len(ops) > 0:
            op = ops[0]
        else:
            raise ImproperlyConfigured('Need at least one Operation'
                ' to use for this test'
            )

        workspace_with_resource = None
        all_workspaces = Workspace.objects.all()
        for w in all_workspaces:
            if len(w.resources.all()) > 0:
                workspace_with_resource = w

        mock_used_resource = workspace_with_resource.resources.all()[0]
        mock_validated_inputs = {
            'count_matrix': str(mock_used_resource.pk), 
            'p_val': 0.01
        }

        executed_op_pk = uuid.uuid4()
        ex_op = WorkspaceExecutedOperation.objects.create(
            id=executed_op_pk,
            owner = self.regular_user_1, 
            workspace = workspace_with_resource,
            job_name = 'abc',
            inputs = mock_validated_inputs,
            outputs = {},
            operation = op,
            mode = 'local_docker',
            status = ExecutedOperation.SUBMITTED
        )

        # can use any random resource which acts like
        # a mock output where we would use the ex_op
        # as the `parent_operation`
        r = Resource.objects.all()
        r = r[0]
        d = {
            RESOURCE_KEY: r.pk,
            PARENT_OP_KEY: ex_op.pk
        }
        # delete any existing metadata on this resource (in case it's there
        # from a prior test)
        rr = ResourceMetadata.objects.filter(resource=r)
        if len(rr) == 1:
             rr.delete()
        rms = ResourceMetadataSerializer(data=d)
        rms.is_valid(raise_exception=True)
        self.assertTrue(rms.is_valid())
        rm = rms.save()
        self.assertIsNone(rm.observation_set)
        self.assertIsNone(rm.feature_set)
        self.assertEqual(ex_op.pk, rm.parent_operation.pk)

        # try again, but now give it a non-existent reference
        # to an executed op:
        d = {
            RESOURCE_KEY: r.pk,
            PARENT_OP_KEY: uuid.uuid4()
        }
        # delete any existing metadata on this resource (in case it's there
        # from a prior test)
        rr = ResourceMetadata.objects.filter(resource=r)
        if len(rr) == 1:
             rr.delete()
        rms = ResourceMetadataSerializer(data=d)
        with self.assertRaisesRegex(ValidationError, 'does not exist'):
            rms.is_valid(raise_exception=True)

    def test_respects_null_attribute_context(self):
        '''
        This tests that passing `allow_null_attributes` via the context 
        kwarg works as expected
        '''
        mock_obs_set = {
            'elements': [
                {
                    'id': 'sampleA',
                    'attributes' : {
                        "alcohol_history": {
                            "attribute_type": "UnrestrictedString",
                            "value": "yes"
                        },
                        "age_at_index": {
                            "attribute_type": "Float",
                            "value": 13.2
                        },
                    }
                },
                {
                    'id': 'sampleB',
                    'attributes' : {
                        "alcohol_history": {
                            "attribute_type": "UnrestrictedString",
                            "value": "yes"
                        },
                        "age_at_index": {
                            "attribute_type": "Float",
                            "value": None
                        },
                    }
                }
            ]
        }
        r = Resource.objects.all()
        r = r[0]
        d = {
            RESOURCE_KEY: r.pk,
            OBSERVATION_SET_KEY: mock_obs_set,
            FEATURE_SET_KEY: None,
            PARENT_OP_KEY:None
        }
        # pass the proper kwarg to allow the None/null:
        rms = ResourceMetadataSerializer(data=d, context={'permit_null_attributes': True})
        self.assertTrue(rms.is_valid())

        # try without any kwarg-- should fail since we implicitly do not allow None unless dictated
        rms = ResourceMetadataSerializer(data=d)
        with self.assertRaises(ValidationError):
            rms.is_valid(raise_exception=True)

        # explicitly deny nulls-- should fail
        rms = ResourceMetadataSerializer(data=d, context={'permit_null_attributes': False})
        with self.assertRaises(ValidationError):
            rms.is_valid(raise_exception=True)