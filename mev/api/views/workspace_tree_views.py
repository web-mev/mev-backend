import logging

from django.conf import settings

from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from api.utilities.operations import create_workspace_dag
from api.models import Workspace, WorkspaceExecutedOperation

class WorkspaceTreeView(APIView):

    def get(self, request, *args, **kwargs):
        workspace_uuid = kwargs['workspace_pk']
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

        if (request.user.is_staff) or (request.user == workspace.owner):
            executed_ops = WorkspaceExecutedOperation.objects.filter(workspace=workspace)
            dag = create_workspace_dag(executed_ops)
            return Response(dag)
        else:
            raise PermissionDenied()