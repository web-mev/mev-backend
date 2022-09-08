import logging
import datetime
import os
import json
from io import StringIO

from django.conf import settings
from django.core.files.base import File

from rest_framework.exceptions import PermissionDenied, ParseError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from constants import JSON_FILE_KEY, JSON_FORMAT

from api.utilities.operations import create_workspace_dag
from api.utilities.resource_utilities import write_resource, \
    initiate_resource_validation, \
    create_resource
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
        dag = self.get_tree(request, *args, **kwargs)
        fh =File(StringIO(json.dumps(dag)), output_filename)
        try:
            workspace = Workspace.objects.get(pk=kwargs['workspace_pk'])
            resource_instance = create_resource(
                request.user,
                file_handle=fh,
                name=output_filename,
                is_active=False,
                workspace=workspace
            )
        except Exception as ex:
            logger.error('Failed at writing the workspace export.')
            raise ex

        initiate_resource_validation(resource_instance,
            JSON_FILE_KEY,
            JSON_FORMAT
        )
        return Response({}, status=status.HTTP_201_CREATED)