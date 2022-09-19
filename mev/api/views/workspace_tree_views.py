import logging
import datetime
import os
import json
from io import StringIO

from django.core.files.base import File

from rest_framework.exceptions import PermissionDenied, ParseError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from constants import JSON_FILE_KEY, JSON_FORMAT

from api.utilities.resource_utilities import initiate_resource_validation, \
    create_resource, \
    get_resource_by_pk
from api.utilities.operations import get_operation_instance_data
from api.data_structures import SimpleDag, DagNode, DATARESOURCE_TYPENAMES
from api.models import Workspace, WorkspaceExecutedOperation

logger = logging.getLogger(__name__)


class WorkspaceTreeBase(object):

    def create_workspace_dag(self, workspace_executed_ops):
        '''
        Returns a DAG representing the resources and operations contained in a workspace

        `workspace_executed_ops` is a set of ExecutedOperation (database model) objects
        '''
        graph = SimpleDag()
        for exec_op in workspace_executed_ops:

            # don't want to show failed jobs
            if exec_op.job_failed:
                continue

            # we need the operation definition to know if any of the inputs
            # were DataResources
            op = exec_op.operation
            op_data = get_operation_instance_data(op)

            # the operation spec will tell us what the "types" of each input/output are
            op_inputs = op_data['inputs']
            op_outputs = op_data['outputs']

            # the executed ops will have the actual args used. So, for a DataResource
            # "type", it will be a UUID
            exec_op_inputs = exec_op.inputs
            exec_op_outputs = exec_op.outputs

            # create a spec for the executed op that includes the operation spec
            # and the actual inputs/outputs
            full_op_data = {
                'op_spec': op_data,
                'inputs': exec_op_inputs,
                'outputs': exec_op_outputs
            }

            # create a node for the operation
            op_node = DagNode(str(exec_op.pk), 
                DagNode.OP_NODE, 
                node_name = op_data['name'],
                op_data = full_op_data)
            graph.add_node(op_node)

            for k,v in exec_op_inputs.items():
                # compare with the expected type:
                op_input_definition = op_inputs[k]
                op_spec = op_input_definition['spec']
                input_type = op_spec['attribute_type']
                if input_type in DATARESOURCE_TYPENAMES:
                    r = get_resource_by_pk(v)
                    resource_node = graph.get_or_create_node(
                        str(v), 
                        DagNode.DATARESOURCE_NODE, 
                        node_name = r.name)
                    op_node.add_parent(resource_node)

            # show the outputs if the operation has completed
            if exec_op.execution_stop_datetime:
                for k,v in exec_op_outputs.items():
                    # compare with the expected type:
                    op_output_definition = op_outputs[k]
                    op_spec = op_output_definition['spec']
                    output_type = op_spec['attribute_type']
                    if output_type in DATARESOURCE_TYPENAMES:
                        if v is not None:
                            r = get_resource_by_pk(v)
                            resource_node = graph.get_or_create_node(
                                str(v), 
                                DagNode.DATARESOURCE_NODE, 
                                node_name = r.name)
                            resource_node.add_parent(op_node)
        return graph.serialize()

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
            return self.create_workspace_dag(executed_ops)
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