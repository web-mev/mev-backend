import json
import os
from io import BytesIO

from django.urls import reverse
from django.core.exceptions import ImproperlyConfigured
from django.core.files import File

from api.models import Resource, Workspace

from data_structures.observation import Observation
from data_structures.feature import Feature
from data_structures.observation_set import ObservationSet
from data_structures.feature_set import FeatureSet

from api.serializers.resource_metadata import ResourceMetadataSerializer
from constants import OBSERVATION_SET_KEY, \
    FEATURE_SET_KEY, \
    RESOURCE_KEY, \
    PARENT_OP_KEY
from resource_types.table_types import Matrix, FeatureTable
from api.utilities.resource_utilities import add_metadata_to_resource

from api.tests.base import BaseAPITestCase
from api.tests.test_helpers import associate_file_with_resource


def create_observation_set():
    '''
    Utility method to create a dict-representation
    of a valid ObservationSet
    '''
    el1 = {
        'id': 'sampleA',
        'attributes': {
            'phenotype': {
                'attribute_type': 'String',
                'value': 'WT'
            }
        }
    }

    el2 = {
        'id': 'sampleB',
        'attributes': {
            'phenotype': {
                'attribute_type': 'String',
                'value': 'KO'
            }
        }
    }

    # the correct serialized representation of an ElementSet instance
    observation_set_data = {
        'elements': [
            el1,
            el2
        ]
    }
    obs_set = ObservationSet(observation_set_data)
    return obs_set.to_dict()


def create_feature_set():
    '''
    Utility method to create a dict-representation
    of a valid FeatureSet
    '''
    el1 = {
        'id': 'featureA',
        'attributes': {
            'pathway': {
                'attribute_type': 'String',
                'value': 'foo'
            }
        }
    }

    el2 = {
        'id': 'featureB',
        'attributes': {
            'pathway': {
                'attribute_type': 'String',
                'value': 'bar'
            }
        }
    }

    feature_set_data = {
        'elements': [
            el1,
            el2
        ]
    }
    fs = FeatureSet(feature_set_data)
    return fs.to_dict()


class TestWorkspaceMetadata(BaseAPITestCase):

    def setUp(self):
        self.establish_clients()

        self.new_resource1 = Resource.objects.create(
            name='foo.txt',
            owner=self.regular_user_1,
            is_active=True,
            datafile=File(BytesIO(), 'foo.txt')
        )
        self.new_resource2 = Resource.objects.create(
            name='bar.txt',
            owner=self.regular_user_1,
            is_active=True,
            datafile=File(BytesIO(), 'bar.txt')
        )
        self.new_resource3 = Resource.objects.create(
            name='baz.txt',
            owner=self.regular_user_1,
            is_active=True,
            datafile=File(BytesIO(), 'baz.txt')
        )

        # create a workspace to which we will eventually add resources
        self.workspace = Workspace.objects.create(
            owner=self.regular_user_1
        )

        self.empty_workspace = Workspace.objects.create(
            owner=self.regular_user_1
        )

        obs1_data = {
            'id': 'sampleA',
            'attributes': {
                'phenotype': {
                    'attribute_type': 'String',
                    'value': 'WT'
                }
            }
        }

        obs2_data = {
            'id': 'sampleB',
            'attributes': {
                'phenotype': {
                    'attribute_type': 'String',
                    'value': 'KO'
                }
            }
        }

        obs3_data = {
            'id': 'sampleC',
            'attributes': {
                'phenotype': {
                    'attribute_type': 'String',
                    'value': 'KO'
                }
            }
        }
        # this ensures they are formatted correctly
        obs1 = Observation(obs1_data)
        obs2 = Observation(obs2_data)
        obs3 = Observation(obs3_data)

        feature1_data = {
            'id': 'featureA',
            'attributes': {
                'pathway': {
                    'attribute_type': 'String',
                    'value': 'foo'
                }
            }
        }

        feature2_data = {
            'id': 'featureB',
            'attributes': {
                'pathway': {
                    'attribute_type': 'String',
                    'value': 'bar'
                }
            }
        }

        feature3_data = {
            'id': 'featureC',
            'attributes': {
                'pathway': {
                    'attribute_type': 'String',
                    'value': 'baz'
                }
            }
        }

        feature4_data = {
            'id': 'featureD',
            'attributes': {
                'pathway': {
                    'attribute_type': 'String',
                    'value': 'bar'
                }
            }
        }

        # this ensures they are formatted correctly:
        feature1 = Feature(feature1_data)
        feature2 = Feature(feature2_data)
        feature3 = Feature(feature3_data)
        feature4 = Feature(feature4_data)

        # create an ObservationSet for resource1
        observation_set_data1 = {
            'elements': [
                obs1_data,
                obs2_data
            ]
        }
        # create an ObservationSet for resource2
        observation_set_data2 = {
            'elements': [
                obs3_data,
            ]
        }

        # create a FeatureSet for resource1
        feature_set_data1 = {
            'elements': [
                feature1_data,
                feature2_data
            ]
        }

        # create a FeatureSet for resource2
        feature_set_data2 = {
            'elements': [
                feature3_data,
                feature4_data
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
            kwargs={'workspace_pk': self.empty_workspace.pk}
        )
        response = self.authenticated_regular_client.get(url)
        response_json = response.json()
        self.assertEqual(response_json['results'], [])

        # test for feature sets
        url = reverse(
            'workspace-features-metadata',
            kwargs={'workspace_pk': self.empty_workspace.pk}
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
            kwargs={'workspace_pk': self.workspace.pk}
        )
        response = self.authenticated_regular_client.get(url)
        response_json = response.json()
        expected_obs = set(['sampleA', 'sampleB', 'sampleC'])
        returned_obs = set()
        for el in response_json['results']:
            returned_obs.add(el['id'])
        self.assertEqual(expected_obs, returned_obs)

        url = reverse(
            'workspace-features-metadata',
            kwargs={'workspace_pk': self.workspace.pk}
        )
        response = self.authenticated_regular_client.get(url)
        response_json = response.json()
        expected_features = set(
            ['featureA', 'featureB', 'featureC', 'featureD'])
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
            kwargs={'workspace_pk': self.workspace.pk}
        )
        response = self.authenticated_regular_client.get(url)
        response_json = response.json()
        expected_obs = set(['sampleA', 'sampleB'])
        returned_obs = set()
        for el in response_json['results']:
            returned_obs.add(el['id'])
        self.assertEqual(expected_obs, returned_obs)

        url = reverse(
            'workspace-features-metadata',
            kwargs={'workspace_pk': self.workspace.pk}
        )
        response = self.authenticated_regular_client.get(url)
        response_json = response.json()
        expected_features = set(['featureA', 'featureB'])
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
            kwargs={'workspace_pk': self.workspace.pk}
        )
        url = baseurl + '?page=1&page_size=2'
        response = self.authenticated_regular_client.get(url)
        response_json = response.json()

        self.assertTrue(len(response_json['results']) == 2)
        expected_obs = ['sampleA', 'sampleB']
        returned_obs = []
        for el in response_json['results']:
            returned_obs.append(el['id'])
        self.assertEqual(expected_obs, returned_obs)

        baseurl = reverse(
            'workspace-features-metadata',
            kwargs={'workspace_pk': self.workspace.pk}
        )
        url = baseurl + '?page=1&page_size=2'
        response = self.authenticated_regular_client.get(url)
        response_json = response.json()
        self.assertTrue(len(response_json['results']) == 2)
        expected = ['featureA', 'featureB']
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
            kwargs={'workspace_pk': self.workspace.pk}
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
            workspace_resources = w.resources.filter(is_active=True)
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
        resource_path = os.path.join(
            TESTDIR, 'deseq_results_example_concat.tsv')
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
            kwargs={'workspace_pk': workspace.pk}
        )
        response = self.authenticated_regular_client.get(url)
        response_json = response.json()
