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

from api.serializers.upload_serializer import UploadSerializer
from api.serializers.resource import ResourceSerializer
import api.permissions as api_permissions
import api.async_tasks as api_tasks
from api.utilities.resource_utilities import create_resource_from_upload, \
    set_resource_to_validation_status

User = get_user_model()

logger = logging.getLogger(__name__)

class ResourceUpload(APIView):
    '''
    Endpoint for a direct upload to the server.
    '''
    parser_classes = [MultiPartParser]

    permission_classes = [framework_permissions.IsAuthenticated]
    serializer_class = UploadSerializer

    def get_serializer(self):
        return self.serializer_class()

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            # the owner key is optional.  If not specified,
            # the uploaded resource will be assigned to the 
            # user originating this request.
            try:
                owner_email = request.data['owner_email']
                try:
                    owner = User.objects.get(email=owner_email)
                except User.DoesNotExist:
                    return Response(
                        {'owner_email': 'Owner email not found.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except KeyError:
                owner = request.user

            # The resource type is NOT required, but may be specified
            resource_type = request.data.get('resource_type')

            # get the remainder of the payload parameters
            upload = request.data['upload_file']
            is_public = request.data.get('is_public', False)

            # grab the file name from the upload request
            # and write to a temporary directory where
            # we stage files pre-validation
            filename = upload.name
            tmp_name = '{uuid}.{filename}'.format(
                uuid = str(uuid.uuid4()),
                filename = filename
            )
            tmp_path = os.path.join(
                settings.PENDING_FILES_DIR, 
                tmp_name
            )

            try:
                with open(tmp_path, 'wb+') as destination:
                    for chunk in upload.chunks():
                        destination.write(chunk)
            except Exception as ex:
                logger.error('An exception was raised when writing a local upload to the tmp directory.')
                logger.error(ex)
                raise APIException('The upload process experienced an error.')

            # create a Resource instance.
            # Note that this also performs validation
            # and temporarily disables the Resource via the `is_active` flag
            resource = create_resource_from_upload(
                tmp_path, 
                filename, 
                resource_type,
                is_public,
                True,
                owner
            )

            resource_serializer = ResourceSerializer(resource, context={'request': request})
            return Response(resource_serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResourceUploadProgress(APIView):
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


