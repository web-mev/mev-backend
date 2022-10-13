import uuid
import logging

from rest_framework.generics import CreateAPIView
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser
from rest_framework import status
from rest_framework.response import Response

from api.serializers.upload_serializer import DropboxUploadSerializer
from api.serializers.resource import ResourceSerializer
from api.uploaders import get_async_uploader, DROPBOX
from api.async_tasks.operation_tasks import submit_async_job

logger = logging.getLogger(__name__)


class ResourceUploadView(CreateAPIView):
    '''
    Endpoint for a direct upload to the server.
    '''
    parser_classes = [MultiPartParser]
    serializer_class = ResourceSerializer

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class AsyncUpload(APIView):
    '''
    Base class for uploads that are performed asynchronously,
    e.g. such as with some third-party API, etc.

    Child classes should define the proper serializer for the 
    request payload and also declare the "type"
    of the uploader class that should be used.
    '''

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, 
            many=True,
            context={'requesting_user': request.user})

        if serializer.is_valid():
            data = serializer.data
            logger.info(f'Requested an async upload with data={data}')
            uploader = get_async_uploader(self.uploader_id)
            logger.info('Based on the storage backend, use'
                f' the following uploader: {uploader}')
            # Below, note that the uploader's `rename_inputs`
            # method is used to convert the data payload (which is 
            # generic for all Dropbox-based uploads) and reformats 
            # it into something that the job runner can use.

            # When we execute typical workspace-based operations, the payload sent from
            # the front-end is specific to that operation and already has the proper input
            # keys. For this upload process here, we want to provide a single URL for
            # all types of uploads. The serializer from the derived class ensures that
            # the request provides the proper fields, but they are still not "ready" to 
            # be used as inputs to the varied upload processes.
            # An example is the Dropbox uploader. The client does not care HOW we perform the upload
            # and, unlike typical operations, we can perform the upload locally (e.g. with
            # the Docker runner) or remotely (via Cromwell). We only want to provide a single endpoint
            # for the Dropbox uploader. We then use the `rename_inputs` method to take those general inputs
            # (e.g. the special dropbox download link) and re-map them to the proper format for 
            # the uploader we will be using.
            data = uploader.rename_inputs(request.user, data)
            logger.info('After reformatting the data for this'
                f' uploader, we have: {data}')

            # since we are creating async upload(s), we need to be able
            # to track them-- we will immediately return the UUID(s) which will
            # identify the job(s)
            job_ids = []
            for item in data:
                job_id = uuid.uuid4()
                submit_async_job.delay(
                    job_id, 
                    uploader.op_id,
                    request.user.pk,
                    None,
                    str(job_id),
                    item)
                logger.info(f'Submitted an async upload with ID={job_id}')
                job_ids.append(job_id)
            
            return Response(
                {'upload_ids': job_ids}, 
                status=status.HTTP_200_OK
            )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DropboxUpload(AsyncUpload):
    '''
    Endpoint for uploading resources from Dropbox

    Depending on the storage backend, the files will be uploaded locally
    or in the remote storage. Either way, the same endpoint is used.
    '''
    serializer_class = DropboxUploadSerializer
    uploader_id = DROPBOX

    def get_serializer(self):
        return self.serializer_class()

