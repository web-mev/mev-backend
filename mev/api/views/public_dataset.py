import logging

from rest_framework import permissions as framework_permissions
from rest_framework.generics import ListAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from api.serializers.public_dataset import PublicDatasetSerializer
from api.models import PublicDataset
from api.public_data import check_if_valid_public_dataset_name

from api.async_tasks.public_data_tasks import prepare_dataset

logger = logging.getLogger(__name__)


class PublicDatasetList(ListAPIView):
    '''
    This allows listing of the available public datasets.
    '''
    permission_classes = [
        framework_permissions.IsAuthenticated
    ]

    serializer_class = PublicDatasetSerializer

    def get_queryset(self):
        return PublicDataset.objects.all()


class PublicDatasetAdd(APIView):
    '''
    This view is used by admins to trigger the ingestion and indexing of a public
    dataset. 

    Clearly, the admin must know what they are doing, since each public dataset will
    require all the necessary items to be in place.
    '''

    permission_classes = [
        framework_permissions.IsAdminUser
    ]

    def get(self, request, *args, **kwargs):

        # Get the requested dataset and check that it's valid
        dataset_id = self.kwargs['dataset_id']

        is_valid = check_if_valid_public_dataset_name(dataset_id)

        if is_valid:

            # create a model in the database. This will mark that the process has started
            # and we can update it as the task completes.
            dataset_db_model = PublicDataset.objects.get_or_create(
                active = False, # the default, but we're being explicit here
                index_name = dataset_id
            )
            prepare_dataset.delay(dataset_db_model.pk)
            return Response({}, status=status.HTTP_200_OK) 
        else:
            return Response({}, status=status.HTTP_400_BAD_REQUEST) 


class PublicDatasetQuery(APIView):

    def get(self, request, *args, **kwargs):
        # Get the requested dataset and check that it's valid
        dataset_id = self.kwargs['dataset_id']

        is_valid = check_if_valid_public_dataset_name(dataset_id)

        if is_valid:

            # query solr
            return Response({}, status=status.HTTP_200_OK) 
        else:
            return Response({}, status=status.HTTP_400_BAD_REQUEST) 