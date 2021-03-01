import logging
import json

from django.conf import settings
from rest_framework import permissions as framework_permissions
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from api.models import Resource
from api.serializers.resource import ResourceSerializer
import api.permissions as api_permissions
from api.utilities.operations import check_for_resource_operations
from api.utilities.resource_utilities import get_resource_view, \
    get_resource_paginator, \
    set_resource_to_inactive, \
    resource_supports_pagination
from api.async_tasks.async_resource_tasks import delete_file as async_delete_file
from api.async_tasks.async_resource_tasks import validate_resource as async_validate_resource
from api.exceptions import NonIterableContentsException
from resource_types import ParseException


logger = logging.getLogger(__name__)

class ResourceList(generics.ListCreateAPIView):
    '''
    Lists available Resource instances.

    Admins can list all available Resources.
    
    Non-admin users can only view their own Resources.
    '''
    
    permission_classes = [
        # admins can do anything
        framework_permissions.IsAdminUser | 

        # regular users need to be authenticated
        # AND are only allowed to list Resources.
        (framework_permissions.IsAuthenticated 
        & 
        api_permissions.ReadOnly)
    ]

    serializer_class = ResourceSerializer

    def get_queryset(self):
        '''
        Note that the generic `permission_classes` applied at the class level
        do not provide access control when accessing the list.  

        This method dictates that behavior.
        '''
        user = self.request.user
        if user.is_staff:
            return Resource.objects.all()
        return Resource.objects.filter(owner=user)
    
    def perform_create(self, serializer):
        '''
        This method is called when the serializer creates the class
        Note that only admins can directly create Resources
        (other users have to initiate an upload)
        '''

        # until the validation is complete, the resource_type should
        # be None.  Pop that field off the validated data:
        requested_resource_type = serializer.validated_data.pop('resource_type')


        resource = serializer.save(requesting_user=self.request.user)
        if requested_resource_type:
            set_resource_to_inactive(resource)

            async_validate_resource.delay(
                resource.pk, 
                requested_resource_type 
            )


class ResourceDetail(generics.RetrieveUpdateDestroyAPIView):
    '''
    Retrieves a specific Resource instance.

    Admins can get/modify any Resource.
    
    Non-admin users can only view/edit their own Resources.
    '''

    # Admins can view/update/delete anyone's Resources, but general users 
    # can only modify their own
    permission_classes = [api_permissions.IsOwnerOrAdmin, 
        framework_permissions.IsAuthenticated
    ]

    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer

    def perform_update(self, serializer):
        '''
        Adds the requesting user to the request payload
        '''
        serializer.save(requesting_user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        '''
        When we receive a delete/destroy request, we have to ensure we
        are not deleting critical data.

        Thus, if a Resource is associated with one or more Workspaces, then
        no action will happen. 
        '''

        instance = self.get_object()
        logger.info('Requesting deletion of Resource: {resource}'.format(
            resource=instance))

        if not instance.is_active:
            logger.info('Resource {resource_uuid} was not active.'
                ' Rejecting request for deletion.'.format(
                    resource_uuid = str(instance.pk)
                ))
            return Response(status=status.HTTP_400_BAD_REQUEST)

        if len(instance.workspaces.all()) > 0:

            logger.info('Resource was associated with one or more workspaces'
                ' and cannot be removed.')
            return Response(status=status.HTTP_204_NO_CONTENT)

        # at this point, we have an active Resource associated with
        # zero workspaces. delete.
        # delete the actual file
        async_delete_file.delay(instance.path)
        
        # Now delete the database object:
        self.perform_destroy(instance)
        return Response(status=status.HTTP_200_OK)

class ResourceContents(APIView):
    '''
    Returns the full data underlying a Resource.

    Typically used for small files so that user-interfaces can display
    data

    Depending on the data, the format of the response may be different.
    Additionally, some Resource types do not support a preview.
    
    This returns a JSON-format representation of the data.

    This endpoint is only really sensible for certain types of 
    Resources, such as those in table format.  Other types, such as 
    sequence-based files do not have this functionality.
    '''

    permission_classes = [framework_permissions.IsAuthenticated]

    def check_request_validity(self, user, resource_pk):

        try:
            resource = Resource.objects.get(pk=resource_pk)
        except Resource.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if user.is_staff or (resource.owner == user):
            if not resource.is_active:
                return Response({
                    'resource': 'The requested resource is'
                    ' not active.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # requester can access, resource is active.  Go get preview
            return resource
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)

    def get(self, request, *args, **kwargs):
        user = request.user
        resource_pk=kwargs['pk']
        r = self.check_request_validity(user, resource_pk)
        if not type(r) == Resource:
            # if it's not a Resource, then it was something else, like a Response object
            # If so, return that.
            return r
        else:
            # requester can access, resource is active.  Go get contents
            try:
                contents = get_resource_view(r, request.query_params)
                logger.info('Done getting contents.')
            except ParseException as ex:
                return Response(
                    {'error': 'There was a problem when parsing the request: {ex}'.format(ex=ex)},
                    status=status.HTTP_400_BAD_REQUEST
                )  
            except Exception as ex:
                return Response(
                    {'error': 'Experienced an issue when preparing the resource view: {ex}'.format(ex=ex)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )   
            if contents is None:
                return Response(
                    {'info': 'Contents not available for this resource.'},
                    status=status.HTTP_200_OK
                )
            else:
                if (settings.PAGE_PARAM in request.query_params) and (resource_supports_pagination(r.resource_type)):
                    paginator = get_resource_paginator(r.resource_type)
                    try:
                        results = paginator.paginate_queryset(contents, request)
                    except NonIterableContentsException as ex:
                        # certain resources (e.g. JSON) can support pagination in
                        # certain contexts, such as is the JSON is essentially an 
                        # array. If the paginator raises this error, just return the
                        # entire contents we parsed before.
                        logging.info('Contents of resource ({pk}) were not iterable.'
                            ' Returning all contents.'
                        )
                        return Response(contents)
                    return paginator.get_paginated_response(results)
                else:
                    return Response(contents)