import logging

from rest_framework import permissions as framework_permissions
from rest_framework.generics import ListAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ParseError

from api.serializers.public_dataset import PublicDatasetSerializer
from api.serializers.resource import ResourceSerializer
from api.models import PublicDataset, \
    Workspace
from api.public_data import query_dataset, \
    create_dataset_from_params

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
    '''
    API view which queries a specific dataset using the 
    solr/lucene syntax. The request params essentially get
    passed directly to the solr server and the response
    is a verbatim solr response. However, we put this view
    in the middle in case we might want to modify the response
    at some point.
    '''
    permission_classes = [
        framework_permissions.IsAuthenticated
    ]

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

    permission_classes = [
        framework_permissions.IsAuthenticated
    ]

    def post(self, request, *args, **kwargs):
        try:
            dataset_id = self.kwargs['dataset_id']
        except KeyError as ex:
            message = ('The request to create a public dataset must'
                ' contain the {k} key in the request payload'.format(
                    k = ex
                )
            )
            return Response({'message': message}, status=status.HTTP_400_BAD_REQUEST) 

        # the dataset was ok. Check that we have a 'workspace' key. This endpoint
        # ultimately creates a Resource and we need to add it to the user's workspace
        try:
            workspace_uuid = request.data.pop('workspace')
            request
        except KeyError as ex:
            return Response(
                {'workspace':'Need to supply a workspace UUID with this request'}, 
                status=status.HTTP_400_BAD_REQUEST
            ) 
        
        # Check the existence of the workspace
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

        # ensure this user owns that workspace
        if request.user != workspace.owner:
            raise PermissionDenied()

        try:
            resource_instance = create_dataset_from_params(
                dataset_id, 
                request.user, 
                request.data
            )
            # now add the resource to the workspace
            resource_instance.workspaces.add(workspace)
            resource_instance.save()
            rs = ResourceSerializer(resource_instance, context={'request': request})
            return Response(rs.data, status=status.HTTP_201_CREATED)

        except Exception as ex:
            message = ('The dataset could not be created.'
                ' The reported error message was: {ex}'.format(ex=str(ex))
            )
            return Response({'message': message}, status=status.HTTP_400_BAD_REQUEST)

