import logging 

from rest_framework import generics
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.exceptions import NotFound, ParseError
from rest_framework.response import Response

from api.models import Resource, Workspace
from api.serializers.resource import ResourceSerializer
from api.serializers.workspace_resource import WorkspaceResourceSerializer
from api.serializers.workspace_resource_add import WorkspaceResourceAddSerializer
import api.permissions as api_permissions
from api.utilities.executed_op_utilities import check_for_resource_operations


logger = logging.getLogger(__name__)


class WorkspaceResourceList(generics.ListAPIView):
    '''
    Lists available Resource instances for a particular Workspace.

    '''
    serializer_class = WorkspaceResourceSerializer

    def get_queryset(self):
        '''
        Note that the generic `permission_classes` applied at the class level
        do not provide access control when accessing the list.  

        This method dictates that behavior.
        '''
        workspace_pk = self.kwargs['workspace_pk']
        try:
            workspace = Workspace.objects.get(pk=workspace_pk, owner=self.request.user)
        except Workspace.DoesNotExist:
            raise NotFound()
        if self.request.user == workspace.owner:
            return workspace.resources.all()

def get_workspace_and_resource(workspace_uuid, resource_uuid):
    '''
    Once single function that handles checking the workspace and resource
    ownership and integrity for addition or removal of Resources to a 
    specific Workspace
    '''
    try:
        workspace = Workspace.objects.get(pk=workspace_uuid)
    except Workspace.DoesNotExist:
        logger.info(f'Could not locate Workspace ({workspace_uuid}).')
        raise ParseError({
            'workspace_uuid': \
                f'Workspace referenced by {workspace_uuid} was not found.'})

    try:
        resource = Resource.objects.get(pk=resource_uuid)
    except Resource.DoesNotExist:
        logger.info(f'Could not locate Resource ({resource_uuid})'
        ' when attempting to add/remove Resource to/from'
        f' Workspace ({workspace_uuid}).')
        raise ParseError({
            'resource_uuid': 
                f'Resource referenced by {resource_uuid} was not found'})

    # the workspace and resource must have
    # the same owner.  Requester must be admin or the owner.
    if not (workspace.owner == resource.owner):
        logger.info(f'Resource ({resource_uuid}) and'
            f' workspace ({workspace_uuid}) did not have'
            ' the same owner.  Rejecting request.')
        raise Exception('Workspace and resource did not have the same owner.')
    else:
        return workspace, resource               


class WorkspaceResourceRemove(APIView):
    '''
    This endpoint removes a Resource from a specific Workspace. Note that
    Resources used in one or more Operations cannot be removed from the
    Workspace so that the integrity of analysis workflows is maintained.
    '''

    def get(self, request, *args, **kwargs):
        workspace_uuid = kwargs['workspace_pk']
        resource_uuid = kwargs['resource_pk']
        try:
            workspace, resource = get_workspace_and_resource(
                                    workspace_uuid, resource_uuid)
        except ParseError as ex:
            raise ex
        except Exception as ex:
            return Response({
                    'message':'The owner of the workspace and '
                    'resource must be the same.'
                }, status=status.HTTP_400_BAD_REQUEST
            )

        # at this point, the workspace and resource are valid
        # and have the same owner
        if request.user == workspace.owner:
            # check that the resource is actually in the workspace
            if workspace in resource.workspaces.all():
                # check if the resource was used in any of the operations
                # in that workspace. If it was, we block removal to preserve
                # the integrity of the entire workflow
                resource_was_used_in_workspace = check_for_resource_operations(
                    resource, workspace
                )
                if resource_was_used_in_workspace:
                    return Response(
                        {'message': ('Resource was used in an analysis operation'
                            ' and cannot be removed.')
                        }, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                else: # not used in the workspace
                    resource.workspaces.remove(workspace)
                    return Response(status=status.HTTP_200_OK)
            else:
                # the resource was NOT associated with that workflow
                return Response(                        
                    {'message': ('Resource was not associated with the'
                            ' requested workspace and hence cannot be removed.')
                    }, status=status.HTTP_400_BAD_REQUEST)
        return Response(                        
                        {'message': 'Could not remove the resource from your workspace.'
                        }, status=status.HTTP_400_BAD_REQUEST)


class WorkspaceResourceAdd(APIView):
    '''
    This endpoint adds a Resource instance to a specific Workspace.
    '''
    serializer_class = WorkspaceResourceAddSerializer

    def post(self, request, *args, **kwargs):

        # serializer only really checks that data received was in the correct
        # format.
        serializer = WorkspaceResourceAddSerializer(data=request.data)
        if serializer.is_valid():
            workspace_uuid = kwargs['workspace_pk']
            resource_uuid = str(serializer.validated_data['resource_uuid'])
            logger.info(f'Adding resource ({resource_uuid}) to'
                f' workspace ({workspace_uuid})')

            try:
                workspace, resource = get_workspace_and_resource(workspace_uuid, resource_uuid)
            except ParseError as ex:
                raise ex
            except Exception as ex:
                return Response({
                        'resource_uuid':'The owner of the workspace and '
                        'resource must be the same.'
                    }, status=status.HTTP_400_BAD_REQUEST
                )

            if not resource.is_active:
                logger.info(f'Attempted to add an inactive Resource {resource}'
                    ' to a workspace.')
                raise ParseError('The requested Resource'
                ' is not currently activated, possibly due to pending'
                ' validation.')

            if (resource.resource_type is None) \
                or (resource.file_format is None or resource.file_format == ''):
                logger.info(f'Attempted to add a Resource {resource} without'
                    ' a validated type and format to a workspace.')
                raise ParseError('The requested Resource'
                ' has not been successfully validated.')

            # if here, workspace and resource have the same owner.
            # Now check if the requester is either that same owner
            # or an admin
            requesting_user = request.user
            if (requesting_user.is_staff) or (requesting_user == workspace.owner):
                try:
                    current_workspaces = resource.workspaces.all()
                    if workspace in current_workspaces:
                        return Response(status=status.HTTP_204_NO_CONTENT)
                    else:
                        resource.workspaces.add(workspace)
                        resource.save()
                        rs = ResourceSerializer(resource, context={'request': request})
                        return Response(rs.data, status=status.HTTP_201_CREATED)
                except Exception as ex:
                    logger.error('An exception was raised when adding a resource'
                        f' a {resource_uuid} to workspace {workspace_uuid}.'
                        f'  Exception was: {ex}. \nSee related logs.')
                    return Response({}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                return Response({
                        'resource_uuid':'The owner of the workspace and '
                        'resource must match the requesting user or be'
                        ' requested by admin.'
                    }, status=status.HTTP_400_BAD_REQUEST
                )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
