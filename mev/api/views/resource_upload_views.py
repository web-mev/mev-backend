import uuid
import os
import logging

from django.conf import settings
from django.core.cache import cache
from django.contrib.auth import get_user_model

from rest_framework import permissions as framework_permissions
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser
from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import APIException

from api.models import Resource
from api.serializers.upload_serializer import UploadSerializer, DropboxUploadSerializer
from api.serializers.resource import ResourceSerializer
import api.permissions as api_permissions
from api.uploaders import ServerLocalUpload, \
    get_async_uploader, \
    DROPBOX
from api.async_tasks.operation_tasks import submit_async_job
from api.utilities.resource_utilities import set_resource_to_inactive
from api.async_tasks.async_resource_tasks import store_resource

logger = logging.getLogger(__name__)

class ServerLocalResourceUpload(APIView):
    '''
    Endpoint for a direct upload to the server.
    '''
    parser_classes = [MultiPartParser]
    permission_classes = [framework_permissions.IsAuthenticated]
    serializer_class = UploadSerializer
    upload_handler_class = ServerLocalUpload

    def get_serializer(self):
        return self.serializer_class()

    def post(self, request, *args, **kwargs):

        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():
            upload_handler = self.upload_handler_class()

            # get the file on the server:
            resource = upload_handler.handle_upload(request, serializer.data)
            
            # if we somehow did not create an api.models.Resource instance, bail out.
            if resource is None:
                return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # set and save attributes to prevent "use" of this Resource
            # before it is (potentially) validated and in its final storage location:
            set_resource_to_inactive(resource)

            # since the async function below doesn't have a defined time to operate,
            # set a generic status on the Resource.
            resource.status = Resource.PROCESSING
            resource.save()

            # send to the final storage backend
            store_resource.delay(resource.pk)

            resource_serializer = ResourceSerializer(resource, context={'request': request})
            return Response(resource_serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ServerLocalResourceUploadProgress(APIView):
    '''
    Endpoint for checking the progress of an upload.

    Requests must contain a "X-Progress-ID" header to identify
    the upload they are monitoring.
    '''
    def get(self, request, format=None):
        progress_id = None
        if 'HTTP_X_PROGRESS_ID' in self.request.GET :
            progress_id = request.GET['HTTP_X_PROGRESS_ID']
        elif 'HTTP_X_PROGRESS_ID' in request.META:
            progress_id = request.META['HTTP_X_PROGRESS_ID']
        if progress_id:
            cache_key = "%s_%s" % (
                request.META['REMOTE_ADDR'], progress_id
            )
            data = cache.get(cache_key)
            return Response(data)
        else:
            error_msg = ('Requests must include a "X-Progress-ID" key'
            ' in the header or as a query parameter with the GET request')
            return Response({'errors': error_msg}, status=status.HTTP_400_BAD_REQUEST)


class AsyncUpload(APIView):
    '''
    Base class for uploads that are performed asynchronously, e.g. such as with some third-party API, etc.

    Child classes should define the proper serializer for the request payload and also declare the "type"
    of the uploader class that should be used.
    '''
    permission_classes = [framework_permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, 
            many=True,
            context={'requesting_user': request.user})

        if serializer.is_valid():
            data = serializer.data
            logger.info('Requested an async upload with data={d}'.format(d=data))
            uploader = get_async_uploader(self.uploader_id)
            logger.info('Based on the storage backend, use'
                ' the following uploader: {u}'.format(
                    u = uploader
                )
            )
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
                ' uploader, we have: {d}'.format(d=data)
            )

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
                logger.info('Submitted an async upload with ID={u}'.format(u=str(job_id)))
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

