import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from api.utilities.admin_utils import alert_admins
from api.models import ExecutedOperation
from api.utilities.nextflow_utils import READABLE_STATES, \
    NEXTFLOW_COMPLETED, \
    NEXTFLOW_ERROR, \
    write_final_nextflow_metadata

logger = logging.getLogger(__name__)


class NextflowStatusView(APIView):
    '''
    This endpoint is used for nextflow to communicate the job
    state back to the server.

    Note that the proxy server is configured so that this view
    is effectively forbidden unless called from localhost
    '''
    # The nextflow engine is making the requests and external
    # requests get 403, so we don't bother with tokens-
    permission_classes = [
        AllowAny
    ]

    def post(self, request, format=None):

        data = request.data
        event = data['event']
        run_name = data['runName']
        logger.info(f'Nextflow event ({event}) received for: {run_name}')
        matching_ops = ExecutedOperation.objects.filter(job_id=run_name)
        if len(matching_ops) != 1:
            alert_admins('Unexpected application state encountered when querying for'
                f' a Nextflow job named {run_name}. Expected a single database object'
                f' but found {len(matching_ops)}'
            )
        else:
            matching_op = matching_ops[0]
            if event == NEXTFLOW_COMPLETED:
                # by setting the `status` field, the nextflow
                # runner will know that it's ready for finalization
                matching_op.status = NEXTFLOW_COMPLETED

                # when the job has completed, Nextflow also POSTS metadata about
                # the job stats, success, etc. Save it to the execution directory
                # since there is no way to get this otherwise (e.g. there is no nextflow
                # database which we can query at a later time)
                write_final_nextflow_metadata(data, matching_op.pk)
            elif event == NEXTFLOW_ERROR:
                matching_op.status = READABLE_STATES[event]
                alert_admins(f'Job failure: {matching_op.pk}')
            else:
                matching_op.status = READABLE_STATES[event]
            matching_op.save()
        return Response({})
