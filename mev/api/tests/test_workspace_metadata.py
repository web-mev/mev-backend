import os
from io import BytesIO

from django.urls import reverse
from django.core.exceptions import ImproperlyConfigured
from django.core.files import File

from api.models import Resource, Workspace
from api.data_structures import Observation, \
    Feature, \
    StringAttribute
from api.serializers.observation import ObservationSerializer
from api.serializers.feature import FeatureSerializer
from api.serializers.resource_metadata  import ResourceMetadataSerializer
from resource_types import OBSERVATION_SET_KEY, \
    FEATURE_SET_KEY, \
    RESOURCE_KEY, \
    PARENT_OP_KEY
from resource_types.table_types import Matrix, FeatureTable
from api.utilities.resource_utilities import add_metadata_to_resource

from api.tests.base import BaseAPITestCase
from api.tests.test_helpers import associate_file_with_resource

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
    
class TestWorkspaceMetadata(BaseAPITestCase):

    def setUp(self):
        self.establish_clients()

        self.new_resource1 = Resource.objects.create(
            name = 'foo.txt',
            owner = self.regular_user_1,
            is_active=True,
            datafile=File(BytesIO(), 'foo.txt')
        )
        self.new_resource2 = Resource.objects.create(
            name = 'bar.txt',
            owner = self.regular_user_1,
            is_active=True,
            datafile=File(BytesIO(), 'bar.txt')
        )
        self.new_resource3 = Resource.objects.create(
            name = 'baz.txt',
            owner = self.regular_user_1,
            is_active=True,
            datafile=File(BytesIO(), 'baz.txt')
        )

        # create a workspace to which we will eventually add resources
        self.workspace = Workspace.objects.create(
            owner = self.regular_user_1
        )

        self.empty_workspace = Workspace.objects.create(
            owner = self.regular_user_1
        )

        # create a few Observations to use with the different Resources
        obs1 = Observation('sampleA', {
            'phenotype': StringAttribute('WT')
        })
        obs1_serializer = ObservationSerializer(obs1)

        obs2 = Observation('sampleB', {
            'phenotype': StringAttribute('KO')
        })
        obs2_serializer = ObservationSerializer(obs2)

        obs3 = Observation('sampleC', {
            'phenotype': StringAttribute('KO')
        })
        obs3_serializer = ObservationSerializer(obs3)

        # create Features to use and a corresponding serializer
        feature1 = Feature('featureA', {
            'pathway': StringAttribute('foo')
        })
        feature1_serializer = FeatureSerializer(feature1)

        feature2 = Feature('featureB', {
            'pathway': StringAttribute('bar')
        })
        feature2_serializer = FeatureSerializer(feature2)

        feature3 = Feature('featureC', {
            'pathway': StringAttribute('bar3')
        })
        feature3_serializer = FeatureSerializer(feature3)

        feature4 = Feature('featureD', {
            'pathway': StringAttribute('bar')
        })
        feature4_serializer = FeatureSerializer(feature4)

        # create an ObservationSet for resource1
        observation_set_data1 = {
            'multiple': True,
            'elements': [
                obs1_serializer.data,
                obs2_serializer.data
            ]
        }
        # create an ObservationSet for resource2
        observation_set_data2 = {
            'multiple': True,
            'elements': [
                obs3_serializer.data,
            ]
        }

        # create a FeatureSet for resource1
        feature_set_data1 = {
            'multiple': True,
            'elements': [
                feature1_serializer.data,
                feature2_serializer.data
            ]
        }
        # create a FeatureSet for resource2
        feature_set_data2 = {
            'multiple': True,
            'elements': [
                feature3_serializer.data,
                feature4_serializer.data
            ]
        }

        metadata1 = {
            RESOURCE_KEY: self.new_resource1.pk,
            OBSERVATION_SET_KEY: observation_set_data1,
            FEATURE_SET_KEY: feature_set_data1,
            PARENT_OP_KEY: None
        }
        metadata2 = {
            RESOURCE_KEY: self.new_resource2.pk,
            OBSERVATION_SET_KEY: observation_set_data2,
            FEATURE_SET_KEY: feature_set_data2,
            PARENT_OP_KEY: None
        }
        rms1 = ResourceMetadataSerializer(data=metadata1)
        if rms1.is_valid(raise_exception=True):
            rms1.save()
        rms2 = ResourceMetadataSerializer(data=metadata2)
        if rms2.is_valid(raise_exception=True):
            rms2.save()

    def test_empty_workspace(self):
        '''
        Tests that we get a reasonable response when we query for metadata
        of a workspace that does not have any resources
        '''
        empty_workspace = Workspace.objects.get(pk=self.empty_workspace.pk)
        self.assertTrue(len(empty_workspace.resources.all()) == 0)
        url = reverse(
            'workspace-observations-metadata', 
            kwargs={'workspace_pk':self.empty_workspace.pk}
        )
        response = self.authenticated_regular_client.get(url)
        response_json = response.json()
        self.assertEqual(response_json['results'], [])

        # test for feature sets
        url = reverse(
            'workspace-features-metadata', 
            kwargs={'workspace_pk':self.empty_workspace.pk}
        )
        response = self.authenticated_regular_client.get(url)
        response_json = response.json()
        self.assertEqual(response_json['results'], [])

    def test_metadata_return_case1(self):
        '''
        Here, both resources are added to the workspace so there
        is a non-trivial merging of the metadata
        '''

        # add both resources to the workspace
        self.new_resource1.workspaces.add(self.workspace)
        self.new_resource2.workspaces.add(self.workspace)
        self.new_resource1.save()
        self.new_resource2.save()

        url = reverse(
            'workspace-observations-metadata', 
            kwargs={'workspace_pk':self.workspace.pk}
        )
        response = self.authenticated_regular_client.get(url)
        response_json = response.json()
        expected_obs = set(['sampleA','sampleB','sampleC'])
        returned_obs = set()
        for el in response_json['results']:
            returned_obs.add(el['id'])
        self.assertEqual(expected_obs, returned_obs)

        url = reverse(
            'workspace-features-metadata', 
            kwargs={'workspace_pk':self.workspace.pk}
        )
        response = self.authenticated_regular_client.get(url)
        response_json = response.json()
        expected_features = set(['featureA','featureB','featureC', 'featureD'])
        returned_features = set()
        for el in response_json['results']:
            returned_features.add(el['id'])
        self.assertEqual(expected_features, returned_features)

    def test_metadata_return_case2(self):
        '''
        Here, only one resource is added to the workspace
        '''

        self.new_resource1.workspaces.add(self.workspace)
        self.new_resource1.save()

        url = reverse(
            'workspace-observations-metadata', 
            kwargs={'workspace_pk':self.workspace.pk}
        )
        response = self.authenticated_regular_client.get(url)
        response_json = response.json()
        expected_obs = set(['sampleA','sampleB'])
        returned_obs = set()
        for el in response_json['results']:
            returned_obs.add(el['id'])
        self.assertEqual(expected_obs, returned_obs)

        url = reverse(
            'workspace-features-metadata', 
            kwargs={'workspace_pk':self.workspace.pk}
        )
        response = self.authenticated_regular_client.get(url)
        response_json = response.json()
        expected_features = set(['featureA','featureB'])
        returned_features = set()
        for el in response_json['results']:
            returned_features.add(el['id'])
        self.assertEqual(expected_features, returned_features)

    def test_metadata_pagination(self):
        '''
        Test that we can properly paginate the response. Needed for cases where
        we have single-cell datasets, etc and the list of observation could be 
        very large
        '''

        # add both resources to the workspace
        self.new_resource1.workspaces.add(self.workspace)
        self.new_resource2.workspaces.add(self.workspace)
        self.new_resource1.save()
        self.new_resource2.save()

        baseurl = reverse(
            'workspace-observations-metadata', 
            kwargs={'workspace_pk':self.workspace.pk}
        )
        url = baseurl + '?page=1&page_size=2'
        response = self.authenticated_regular_client.get(url)
        response_json = response.json()
        self.assertTrue(len(response_json['results']) == 2)
        expected_obs = ['sampleA','sampleB']
        returned_obs = []
        for el in response_json['results']:
            returned_obs.append(el['id'])
        self.assertEqual(expected_obs, returned_obs)

        baseurl = reverse(
            'workspace-features-metadata', 
            kwargs={'workspace_pk':self.workspace.pk}
        )
        url = baseurl + '?page=1&page_size=2'
        response = self.authenticated_regular_client.get(url)
        response_json = response.json()
        self.assertTrue(len(response_json['results']) == 2)
        expected = ['featureA','featureB']
        returned = []
        for el in response_json['results']:
            returned.append(el['id'])
        self.assertEqual(expected, returned)


    def test_with_empty_metadata(self):
        metadata = {
            RESOURCE_KEY: self.new_resource3.pk,
            OBSERVATION_SET_KEY: None,
            FEATURE_SET_KEY: None,
            PARENT_OP_KEY: None
        }
        rms = ResourceMetadataSerializer(data=metadata)
        if rms.is_valid(raise_exception=True):
            rms.save()

        # add resource to the workspace
        self.new_resource3.workspaces.add(self.workspace)
        self.new_resource3.save()

        url = reverse(
            'workspace-observations-metadata', 
            kwargs={'workspace_pk':self.workspace.pk}
        )
        response = self.authenticated_regular_client.get(url)
        response_json = response.json()
        self.assertEqual(response_json['results'], [])

    def test_with_real_files(self):
        '''
        Runs the test with real files rather than providing mocked
        metadata. Not a true unit test, but whatever.
        '''
        # get a workspace in our db:
        workspaces = Workspace.objects.filter(owner=self.regular_user_1)
        if len(workspaces) == 0:
            raise ImproperlyConfigured('Need at least one workspace.')

        workspace = None
        for w in workspaces:
            workspace_resources = w.resources.filter(is_active = True)
            if len(workspace_resources) >= 2:
                workspace = w
        if workspace is None:
            raise ImproperlyConfigured('Need at least two resources that'
                ' are in a workspace. Modify the test database'
            ) 
        # we will attach the metadata to two resources:
        all_resources = workspace.resources.all()
        all_resources = [x for x in all_resources if x.is_active]
    
        TESTDIR = os.path.dirname(__file__)
        TESTDIR = os.path.join(TESTDIR, 'resource_validation_test_files')

        r0 = all_resources[0]
        resource_path = os.path.join(TESTDIR, 'deseq_results_example_concat.tsv')
        self.assertTrue(os.path.exists(resource_path))
        associate_file_with_resource(r0, resource_path)
        t = FeatureTable()
        metadata0 = t.extract_metadata(r0)
        add_metadata_to_resource(r0, metadata0)

        r1 = all_resources[1]
        resource_path = os.path.join(TESTDIR, 'test_matrix.tsv')
        self.assertTrue(os.path.exists(resource_path))
        associate_file_with_resource(r1, resource_path)
        m = Matrix()
        metadata1 = m.extract_metadata(r1)
        add_metadata_to_resource(r1, metadata1)
        url = reverse(
            'workspace-observations-metadata', 
            kwargs={'workspace_pk':workspace.pk}
        )
        response = self.authenticated_regular_client.get(url)
        response_json = response.json()