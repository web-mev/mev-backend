import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

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
        # TODO: create logic upon event receipt
        data = request.data
        logger.info(f'Nextflow event received: {data["event"]}')
        return Response({})
