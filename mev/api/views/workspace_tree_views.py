import logging
import datetime
import os
import json

from django.conf import settings

from rest_framework.exceptions import PermissionDenied, ParseError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from api.utilities.operations import create_workspace_dag
from api.utilities.resource_utilities import validate_and_store_resource, write_resource
from api.models import Workspace, WorkspaceExecutedOperation, Resource

logger = logging.getLogger(__name__)

class WorkspaceTreeBase(object):

    def get_tree(self, request, *args, **kwargs):
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
            return create_workspace_dag(executed_ops)
        else:
            raise PermissionDenied()


class WorkspaceTreeView(APIView, WorkspaceTreeBase):

    def get(self, request, *args, **kwargs):
        dag = self.get_tree(request, *args, **kwargs)
        return Response(dag)


class WorkspaceTreeSave(APIView, WorkspaceTreeBase):

    def get(self, request, *args, **kwargs):
        timestamp_str = datetime.datetime.now().strftime('%m-%d-%Y-%H-%M-%S')
        output_filename = 'workspace_export.{workspace_id}.{timestamp}.json'.format(
            workspace_id = str(kwargs['workspace_pk']),
            timestamp = timestamp_str
        )
        user_uuid = str(request.user.user_uuid)
        tmp_path = os.path.join(
            settings.RESOURCE_CACHE_DIR, 
            user_uuid,
            output_filename
        )
        dag = self.get_tree(request, *args, **kwargs)

        try:
            write_resource(json.dumps(dag), tmp_path)
        except Exception as ex:
            logger.error('Failed at writing the workspace export.')
            raise ex

        resource_instance = Resource.objects.create(
            owner = request.user,
            path = tmp_path,
            name = output_filename
        )
        workspace = Workspace.objects.get(pk=kwargs['workspace_pk'])
        resource_instance.workspaces.add(workspace)
        resource_instance.save()
        validate_and_store_resource(resource_instance, 'JSON')
        return Response({}, status=status.HTTP_201_CREATED)