import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ParseError, PermissionDenied

from api.models import Workspace, ResourceMetadata
from api.serializers.observation_set import NullableObservationSetSerializer, ObservationSetSerializer
from api.serializers.feature_set import NullableFeatureSetSerializer, FeatureSetSerializer
from api.data_structures import merge_element_set

logger = logging.getLogger(__name__)

from resource_types import OBSERVATION_SET_KEY, FEATURE_SET_KEY

class WorkspaceMetadataView(APIView):

    # this allows us to change the serializer class in a single location
    observation_set_serializer_class = NullableObservationSetSerializer
    feature_set_serializer_class = NullableFeatureSetSerializer

    def get_element_set(self, feature_or_obs_data, element_set_serializer_class):
        s = element_set_serializer_class(data=feature_or_obs_data)
        if s.is_valid():
            return s.get_instance()
        else:
            logger.error('The data to create a {t}'
                ' has been corrupted.'.format(t=element_set_serializer_class))
            raise Exception('The data to create a {t}'
                ' has been corrupted.'.format(t=element_set_serializer_class))
        

    def get_merged_element_sets(self, all_metadata, serializer_class, field):
        '''
        A common way to handle the creation of merged ObservationSet or
        FeatureSet instances

        `all_metadata` is a list of ResourceMetadata corresponding to the 
          Resources that are in a single Workspace
        `serializer_class` is a class that implements the correct serializer.
          This is either ObservationSetSerializer or FeatureSetSerializer
        `field` is the attribute we are looking for- e.g. 'observation_set'
          or 'feature_set'
        '''
        all_sets = []
        for metadata in all_metadata:
            set_data = getattr(metadata, field)
            if set_data is not None:
                element_set = self.get_element_set(set_data, serializer_class)
                all_sets.append(element_set)
        full_set = merge_element_set(all_sets)
        s = serializer_class(full_set)
        return s.data

    def get_workspace(self, workspace_uuid, requesting_user):
        try:
            workspace = Workspace.objects.get(pk=workspace_uuid)
        except Workspace.DoesNotExist:
            logger.info('Could not locate Workspace ({workspace_uuid}).'.format(
                workspace_uuid = str(workspace_uuid)
                )
            )
            raise ParseError({
                'workspace_uuid': 'Workspace referenced by {uuid}'
                ' was not found.'.format(uuid=workspace_uuid)
            })

        if (requesting_user.is_staff) or (requesting_user == workspace.owner):
            return workspace
        else:
            raise PermissionDenied()

    def fetch_metadata(self, request, *args, **kwargs):

        # if the workspace lookup fails or if the user was not allowed to access
        # the workspace, then exceptions raised there will percolate up if we don't
        # catch them here
        workspace_uuid = kwargs['workspace_pk']
        workspace = self.get_workspace(workspace_uuid, request.user)

        # now get all the resources associated with the workspace
        workspace_resources = workspace.resources.all()
        all_metadata = ResourceMetadata.objects.filter(resource__in = workspace_resources)
        return all_metadata

    def get(self, request, *args, **kwargs):
        
        all_metadata = self.fetch_metadata(request, *args, **kwargs)
        if len(all_metadata) == 0:
            return Response(
                {
                    OBSERVATION_SET_KEY: None,
                    FEATURE_SET_KEY: None
                }
            )
        full_obs_set_data = self.get_merged_element_sets(all_metadata, 
            self.observation_set_serializer_class, OBSERVATION_SET_KEY)
        full_feature_set_data = self.get_merged_element_sets(all_metadata, 
            self.feature_set_serializer_class, FEATURE_SET_KEY)
        return Response(
            {
                OBSERVATION_SET_KEY: full_obs_set_data,
                FEATURE_SET_KEY: full_feature_set_data
            }
        )


class WorkspaceMetadataObservationsView(WorkspaceMetadataView):
        
    def get(self, request, *args, **kwargs):
        all_metadata = self.fetch_metadata(request, *args, **kwargs)
        full_obs_set_data = self.get_merged_element_sets(all_metadata, 
            self.observation_set_serializer_class, OBSERVATION_SET_KEY)
        return Response(
            {
                OBSERVATION_SET_KEY: full_obs_set_data
            }
        )


class WorkspaceMetadataFeaturesView(WorkspaceMetadataView):
    def get(self, request, *args, **kwargs):
        
        all_metadata = self.fetch_metadata(request, *args, **kwargs)
        print(all_metadata)
        full_feature_set_data = self.get_merged_element_sets(all_metadata, 
            self.feature_set_serializer_class, FEATURE_SET_KEY)
        return Response(
            {
                FEATURE_SET_KEY: full_feature_set_data
            }
        )