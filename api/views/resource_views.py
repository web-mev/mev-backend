import logging

from rest_framework import permissions as framework_permissions
from rest_framework import generics
from rest_framework import status
from rest_framework.response import Response

from api.models import Resource
from api.serializers import ResourceSerializer
import api.permissions as api_permissions
from api.utilities.resource_utilities import check_for_resource_operations, \
    check_for_shared_resource_file
import api.async_tasks as api_tasks

logger = logging.getLogger(__name__)

class ResourceList(generics.ListCreateAPIView):
    '''
    Lists available Resource instances.

    Admins can list all available Resources, but non-admin users 
    can only view their own Resources.
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
        serializer.save(requesting_user=self.request.user)


class ResourceDetail(generics.RetrieveUpdateDestroyAPIView):

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
            api_tasks.delete_file.delay(instance.path, instance.is_local)
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
