import logging

from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import ParseError, PermissionDenied
from rest_framework.response import Response

from exceptions import WebMeVException
from constants import OBSERVATION_SET_KEY, FEATURE_SET_KEY

from data_structures.observation_set import ObservationSet
from data_structures.feature_set import FeatureSet

from api.models import Workspace, ResourceMetadata
from api.serializers.resource_metadata import ResourceMetadataObservationsSerializer, \
    ResourceMetadataFeaturesSerializer


logger = logging.getLogger(__name__)


class MetadataPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 1000


class WorkspaceMetadataBase(object):

    paginator = MetadataPagination

    def get_element_set_instance(self, data):
        '''
        Turns the json/dict `data` (which denotes either an ObservationSet
        or FeatureSet into an instance of a data structure so that we can 
        perform merging operations
        '''
        try:
            return self.set_type(data)
        except WebMeVException as ex:
            logger.error('The data to create an element set'
                         ' has been corrupted.')
            raise ex

    def get_merged_element_sets(self, all_metadata, field):
        '''
        A common way to handle the creation of merged ObservationSet or
        FeatureSet instances

        `all_metadata` is a list of ResourceMetadata corresponding to the 
          Resources that are in a single Workspace
        `field` is the attribute we are looking for- e.g. 'observation_set'
          or 'feature_set'
        '''
        # create an empty set to start. We will then perform
        # union operations to create the complete set of Observations
        # or Feature across all resources.
        union_set = self.set_type({'elements': []})
        for metadata in all_metadata:
            set_data = getattr(metadata, field)
            if set_data is not None:
                element_set = self.get_element_set_instance(set_data)
                union_set = union_set.set_union(element_set)
        return union_set

    def get_workspace(self, workspace_uuid, requesting_user):
        try:
            workspace = Workspace.objects.get(pk=workspace_uuid)
        except Workspace.DoesNotExist:
            logger.info('Could not locate Workspace ({workspace_uuid}).'.format(
                workspace_uuid=str(workspace_uuid)
            )
            )
            raise ParseError({
                'workspace_uuid': 'Workspace referenced by {uuid}'
                ' was not found.'.format(uuid=workspace_uuid)
            })

        if requesting_user == workspace.owner:
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
        all_metadata = ResourceMetadata.objects.filter(
            resource__in=workspace_resources)
        return self.get_merged_element_sets(all_metadata, key)

    def _paginate_response(self, element_set):

        sorted_elements = sorted(list(element_set.elements), key=lambda x: x.id)

        # take the 'value' field from the dict representation. Recall that
        # the `to_dict` method called on a child of
        # data_structures.elememt.Element looks like
        # {
        #     'attribute_type': "Observation",
        #     'value': {
        #         'id': 'abc',
        #         'attributes': {...}
        #     }
        # }
        element_list = [x.to_dict()['value'] for x in sorted_elements]
        page = self.paginate_queryset(element_list)
        if page is not None:
            return self.get_paginated_response(page)
        return Response(element_list)

class WorkspaceMetadataObservationsView(ListAPIView, WorkspaceMetadataBase):

    '''
    This view class will return a set of `Observation `instances that reside
    in a given workspace (returned as an `ObservationSet`) 
    '''
    pagination_class = MetadataPagination

    # This creates the proper type in the methods we inherit
    # from `WorkspaceMetadataBase`
    set_type = ObservationSet

    def list(self, request, *args, **kwargs):
        obs_set = self.fetch_metadata(OBSERVATION_SET_KEY)
        return self._paginate_response(obs_set)


class WorkspaceMetadataFeaturesView(ListAPIView, WorkspaceMetadataBase):
    pagination_class = MetadataPagination

    # This creates the proper type in the methods we inherit
    # from `WorkspaceMetadataBase`
    set_type = FeatureSet

    def list(self, request, *args, **kwargs):
        feature_set = self.fetch_metadata(FEATURE_SET_KEY)
        return self._paginate_response(feature_set)