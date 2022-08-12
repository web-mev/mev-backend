import logging

from django.http import Http404
from rest_framework.exceptions import APIException
from rest_framework.generics import RetrieveAPIView

from api.models import Resource, ResourceMetadata
from api.serializers.resource_metadata import ResourceMetadataSerializer, \
    ResourceMetadataObservationsSerializer, \
    ResourceMetadataFeaturesSerializer, \
    ResourceMetadataParentOperationSerializer

logger = logging.getLogger(__name__)

class ResourceMetadataView(RetrieveAPIView):

    serializer_class = ResourceMetadataSerializer

    def get_queryset(self):
        resource_uuid = self.kwargs['pk']
        try:
            resource = Resource.objects.get(pk=resource_uuid)
        except Resource.DoesNotExist:
            raise Http404
        if resource.is_active:
            return ResourceMetadata.objects.filter(resource=resource)
        else:
            logger.info('Resource associated with the requested metadata'
            ' is inactive.')
            return []

    def get_object(self):
        queryset = self.get_queryset()
        if len(queryset) == 0:
            raise Http404
        elif len(queryset) == 1:
            return queryset[0]
        else:
            logger.error('Database constraint violated.'
                ' There were >1 metadata instances associated with'
                ' a Resource ({resource_uuid})'.format(
                    resource_uuid=self.kwargs['pk'])
            )
            raise APIException()

class ResourceMetadataObservationsView(ResourceMetadataView):
    serializer_class = ResourceMetadataObservationsSerializer

class ResourceMetadataFeaturesView(ResourceMetadataView):
    serializer_class = ResourceMetadataFeaturesSerializer

class ResourceMetadataParentOperationView(ResourceMetadataView):
    serializer_class = ResourceMetadataParentOperationSerializer