import logging
import json

from rest_framework import permissions as framework_permissions
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response

from api.models import Resource
from api.serializers.resource import ResourceSerializer
import api.permissions as api_permissions
from api.utilities.resource_utilities import check_for_resource_operations, \
    check_for_shared_resource_file, \
    get_resource_preview, \
    set_resource_to_validation_status

import api.async_tasks as api_tasks

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
        # until the validation is complete, the resource_type should
        # be None.  Pop that field off the validated data:
        requested_resource_type = serializer.validated_data.pop('resource_type')
        resource = serializer.save(requesting_user=self.request.user)
        if requested_resource_type:
            set_resource_to_validation_status(resource)

            api_tasks.validate_resource.delay(
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

        Note that when we attach a Resource to a Workspace, we create a second
        database record that references the same underlying file/data.  Thus,
        a deletion request has two components to consider:
        - deleting the database record
        - deleting the actual file

        When we go to remove a database record, if there no other records referencing
        the same file, we ALSO delete the file.  If there are other records
        that DO reference the same file, we only delete the requested database
        record.

        In addition, if an attached Resource CANNOT be removed if it has been used
        in any analysis operations.

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

        try:
            file_shared_by_multiple_resources = check_for_shared_resource_file(instance)
            logger.info('File underlying the deleted Resource is '
            ' referenced by multiple Resource instances: {status}'.format(
                status=file_shared_by_multiple_resources
            ))
        except Exception as ex:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if instance.workspace is not None:

            # check if the Resource has been used.  If yes, can't delete
            has_been_used = check_for_resource_operations(instance)

            logger.info('Resource was associated with a workspace ({workspace_uuid})'
                ' and was used:{used}'.format(
                    workspace_uuid=instance.workspace.pk,
                    used=has_been_used
                )
            )

            if has_been_used:
                return Response(status=status.HTTP_400_BAD_REQUEST)

        if not file_shared_by_multiple_resources:
            api_tasks.delete_file.delay(instance.path)
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ResourcePreview(APIView):
    '''
    Returns a preview of the data underlying a Resource.

    Typically used for checking that the parsing of a file worked
    correctly and is formatted properly.

    Depending on the data, the format of the response may be different.
    Additionally, some Resource types do not support a preview.
    '''
    # For certain types of Resource objects, the users may like to see
    # a preview of how the data was parsed, like a unix `head` call.  
    # This returns a JSON-format representation of the data.

    # This preview endpoint is only really sensible for certain types of 
    # Resources, such as those in table format.  Other types, such as 
    # sequence-based files do not have preview functionality.
    

    permission_classes = [framework_permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        try:
            resource = Resource.objects.get(pk=kwargs['pk'])
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
            j = get_resource_preview(resource)
            if 'error' in j:
                return Response(json.dumps(j), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            return Response(json.dumps(j), status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)
