import logging

from django.shortcuts import get_object_or_404
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from api.serializers.public_dataset import PublicDatasetSerializer
from api.models import PublicDataset
from api.public_data import query_dataset
from api.async_tasks.public_data import async_create_dataset_from_params

logger = logging.getLogger(__name__)


class PublicDatasetList(ListAPIView):
    '''
    This allows listing of the available public datasets.
    '''

    serializer_class = PublicDatasetSerializer

    def get_queryset(self):
        return PublicDataset.objects.filter(active=True)


class PublicDatasetDetails(RetrieveAPIView):
    '''
    This allows retrieval of details about a single public dataset.
    '''

    serializer_class = PublicDatasetSerializer
    queryset = PublicDataset.objects.filter(active=True)
    lookup_field = 'dataset_id'

    def get_object(self):
        queryset = self.get_queryset()
        filters = {'index_name': self.kwargs['dataset_id']}
        return get_object_or_404(queryset, **filters)


class PublicDatasetQuery(APIView):
    '''
    API view which queries a specific dataset using the 
    solr/lucene syntax. The request params essentially get
    passed directly to the solr server and the response
    is a verbatim solr response. However, we put this view
    in the middle in case we might want to modify the response
    at some point.
    '''

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
                f' contain the {ex} key in the request payload')
            return Response({'message': message}, status=status.HTTP_400_BAD_REQUEST) 

        # The payload had the proper keyword args. Make the query
        try:
            query_response = query_dataset(dataset_id, query_str)
            return Response(query_response, status=status.HTTP_200_OK) 
        except Exception as ex:
            # TODO: catch a more specific exception?
            return Response({'message': str(ex)}, status=status.HTTP_400_BAD_REQUEST) 


class PublicDatasetCreate(APIView):
    '''
    Creates a dataset for a user based on the POSTed payload.

    Since each dataset instance (e.g. TCGA, CCLE, etc.) may have
    specific mechanisms for creating the dataset, most of the work
    is done by the implementing dataset.

    As an example, consider the TCGA dataset. To cope with the large size
    and slow subsetting of a >2Gb matrix, we use HDF5 storage and organize
    by the TCGA cancer types. Thus, we need more than just the sample IDs when
    we filter-- we also need the cancer type.

    The result of a successful request to this endpoint is the creation of a Resource
    in a user's workspace.
    '''

    def post(self, request, *args, **kwargs):

        try:
            dataset_id = self.kwargs['dataset_id']
        except KeyError as ex:
            message = ('The request to create a public dataset must'
                f' contain the {ex} key in the request payload')
            return Response({'message': message}, 
                status=status.HTTP_400_BAD_REQUEST) 

        # get the filter payload. The structure of this depends on the dataset
        # being queried, so we leave that to the implementing class which will
        # raise an exception if it's not formatted correctly.
        # If not specified, filters is set to None, indicating the whole dataset
        # was requested.
        request_filters = request.data.get('filters')
        if (request_filters is not None) and (not type(request_filters) is dict):
            return Response('The "filters" part of the payload'
            ' should be formatted as an object.', status=status.HTTP_400_BAD_REQUEST)

        # users can optionally name the output. 
        # If nothing is passed, we have an auto-naming scheme
        output_name = request.data.get('output_name')
        if not output_name:
            output_name = ''
        try:
            async_create_dataset_from_params.delay(
                dataset_id, 
                request.user.pk, 
                request_filters,
                output_name
            )
            return Response(status=status.HTTP_204_NO_CONTENT)

        except Exception as ex:
            message = ('The dataset could not be created.'
                f' The reported error message was: {ex}')
            return Response({'message': message}, status=status.HTTP_400_BAD_REQUEST)

