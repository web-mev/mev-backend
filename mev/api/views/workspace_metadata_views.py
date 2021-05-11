import logging

from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.exceptions import ParseError, PermissionDenied
from rest_framework import permissions as framework_permissions

from api.models import Workspace, ResourceMetadata
from api.serializers.observation import NullableObservationSerializer
from api.serializers.feature import NullableFeatureSerializer
from api.serializers.observation_set import NullableObservationSetSerializer
from api.serializers.feature_set import NullableFeatureSetSerializer
from api.data_structures import merge_element_set

logger = logging.getLogger(__name__)

from resource_types import OBSERVATION_SET_KEY, FEATURE_SET_KEY


class MetadataPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 1000

class WorkspaceMetadataBase(object):

    paginator = MetadataPagination

    def get_element_set_instance(self, feature_or_obs_data):
        '''
        Turns the json/dict data into an instance of a data structure so that we can
        perform merging operations
        '''
        s = self.set_serializer_class(data=feature_or_obs_data)
        if s.is_valid():
            return s.get_instance()
        else:
            logger.error('The data to create an element set'
                ' has been corrupted.')
            raise Exception('The data to create an element set'
                ' has been corrupted.')
        

    def get_merged_element_sets(self, all_metadata, field):
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
                element_set = self.get_element_set_instance(set_data)
                all_sets.append(element_set)
        full_set = merge_element_set(all_sets)
        return full_set

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

    def fetch_metadata(self, key):
        '''
        key tells us whether we trying to access the observation_set or feature_set
        within the ResourceMetadata instance
        '''
        # if the workspace lookup fails or if the user was not allowed to access
        # the workspace, then exceptions raised there will percolate up if we don't
        # catch them here
        workspace_uuid = self.kwargs['workspace_pk']
        workspace = self.get_workspace(workspace_uuid, self.request.user)
        # now get all the resources associated with the workspace
        workspace_resources = workspace.resources.all()
        all_metadata = ResourceMetadata.objects.filter(resource__in = workspace_resources)
        return self.get_merged_element_sets(all_metadata, key)


class WorkspaceMetadataObservationsView(ListAPIView, WorkspaceMetadataBase):

    '''
    This class will send a set of Observation instances that reside
    in a given workspace. 

    Note that we do NOT use the ObservationSetSerializer class (or its
    nullable sibling) since we can't paginate an ObservationSet. To paginate,
    the "top level" of the data structure has to be an iterable. We do, however,
    rely on all the set-like methods that are available on the ObservationSet
    class to prep the data structure. We then extract the elements attribute/field
    and give that to the serializer. 
    '''
    pagination_class = MetadataPagination

    set_serializer_class = NullableObservationSetSerializer
    serializer_class = NullableObservationSerializer

    permission_classes = [
        framework_permissions.IsAuthenticated
    ]

    def get_queryset(self):
        x = self.fetch_metadata(OBSERVATION_SET_KEY)
        if x:
            return sorted(list(x.elements), key=lambda x: x.id)
        else:
            return []



class WorkspaceMetadataFeaturesView(ListAPIView, WorkspaceMetadataBase):
    pagination_class = MetadataPagination

    set_serializer_class = NullableFeatureSetSerializer
    serializer_class = NullableFeatureSerializer

    permission_classes = [
        framework_permissions.IsAuthenticated
    ]

    def get_queryset(self):
        x = self.fetch_metadata(FEATURE_SET_KEY)
        if x:
            return sorted(list(x.elements), key=lambda x: x.id)
        else:
            return []


