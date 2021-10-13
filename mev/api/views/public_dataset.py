import logging

from rest_framework import permissions as framework_permissions
from rest_framework.generics import ListAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from api.serializers.public_dataset import PublicDatasetSerializer
from api.models import PublicDataset
from api.public_data import query_dataset

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
        return PublicDataset.objects.filter(active=True)


class PublicDatasetQuery(APIView):

    def get(self, request, *args, **kwargs):
        
        try:
            dataset_id = self.kwargs['dataset_id']

            # the actual query to be run is included as a query param
            # string at the end of the url. If it's good enough for 
            # technologies like solr, then it's good for us!
            query_params = request.query_params
            
            # `query_params` is of type QueryDict. Make
            # into an encoded url param:
            query_str = query_params.urlencode()
        except KeyError as ex:
            message = ('The request to query a public dataset must'
                ' contain the {k} key in the request payload'.format(
                    k = ex
                )
            )
            return Response({'message': message}, status=status.HTTP_400_BAD_REQUEST) 

        # The payload had the proper keyword args. Make the query
        try:
            query_response = query_dataset(dataset_id, query_str)
            return Response(query_response, status=status.HTTP_200_OK) 
        except Exception as ex:
            # TODO: catch a more specific exception?
            return Response({'message': str(ex)}, status=status.HTTP_400_BAD_REQUEST) 