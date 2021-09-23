from django.urls import path
from django.conf import settings

from rest_framework_simplejwt import views as jwt_views
from rest_framework.schemas import get_schema_view

import api.views

urlpatterns = [
    path('token/', api.views.TokenObtainView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', api.views.RefreshTokenView.as_view(), name='token_refresh'),

    ##########################################################################

    # views for querying User instances
    path('users/', api.views.UserList.as_view(), name='user-list'),
    path('users/<uuid:pk>/', api.views.UserDetail.as_view(), name='user-detail'),
    path('users/register/', api.views.UserRegisterView.as_view(), name='user-register'),
    path('users/activate/', api.views.UserActivateView.as_view(), name='user-activate'),
    path('users/resend-activation/', api.views.ResendActivationView.as_view(), name='resend-activation'),
    path('users/reset-password/confirm/', api.views.PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('users/reset-password/', api.views.PasswordResetView.as_view(), name='password-reset'),
    path('users/change-password/', api.views.PasswordChangeView.as_view(), name='password-change'),
    path('users/social/google/', api.views.GoogleOauth2View.as_view(), name='google-social'),

    ##################### Views for Workspaces ###############################

    path('workspaces/', api.views.WorkspaceList.as_view(), name='workspace-list'),
    path('workspaces/<uuid:pk>/', api.views.WorkspaceDetail.as_view(), name='workspace-detail'),

    ##################### Views for Resources ################################

    # general endpoints for Resources, regardless of Workspace association
    path('resources/', api.views.ResourceList.as_view(), name='resource-list'),
    path('resources/<uuid:pk>/', api.views.ResourceDetail.as_view(), name='resource-detail'),
    path('resources/<uuid:pk>/contents/', api.views.ResourceContents.as_view(), name='resource-contents'),
    path('resources/add-bucket-resources/', api.views.AddBucketResourceView.as_view(), name='bucket-resource-add'),
    path('resources/<uuid:pk>/metadata/', api.views.ResourceMetadataView.as_view(), name='resource-metadata-detail'),
    path('resources/<uuid:pk>/metadata/observations/', api.views.ResourceMetadataObservationsView.as_view(), name='resource-metadata-observations'),
    path('resources/<uuid:pk>/metadata/features/', api.views.ResourceMetadataFeaturesView.as_view(), name='resource-metadata-features'),
    path('resources/<uuid:pk>/metadata/parent/', api.views.ResourceMetadataParentOperationView.as_view(), name='resource-metadata-parent-operation'),
    path('resources/upload/', api.views.ServerLocalResourceUpload.as_view(), name='resource-upload'),
    path('resources/upload/progress', 
        api.views.ServerLocalResourceUploadProgress.as_view(), 
        name='resource-upload-progress'
    ),
    path('resources/dropbox-upload/', api.views.DropboxUpload.as_view(), name='dropbox-upload'),
    path('resources/download/<uuid:pk>/', api.views.ResourceDownload.as_view(), name='download-resource'),

    # For querying the available types of Resources:
    path('resource-types/', api.views.ResourceTypeList.as_view(), name='resource-type-list'),

    # Resources that are associated with specific Workspaces
    path('workspaces/<uuid:workspace_pk>/resources/', api.views.WorkspaceResourceList.as_view(), name='workspace-resource-list'),
    path('workspaces/<uuid:workspace_pk>/resources/<uuid:resource_pk>/remove/', api.views.WorkspaceResourceRemove.as_view(), name='workspace-resource-remove'),
    path('workspaces/<uuid:workspace_pk>/resources/add/', api.views.WorkspaceResourceAdd.as_view(), name='workspace-resource-add'),

    # endpoints for working with metadata
    path('workspaces/<uuid:workspace_pk>/metadata/observations/', api.views.WorkspaceMetadataObservationsView.as_view(), name='workspace-observations-metadata'),
    path('workspaces/<uuid:workspace_pk>/metadata/features/', api.views.WorkspaceMetadataFeaturesView.as_view(), name='workspace-features-metadata'),

    # endpoints for workspace-agnostic metadata utilities
    path('metadata/intersect/', api.views.MetadataIntersectView.as_view(), name='metadata-intersect'),
    path('metadata/union/', api.views.MetadataUnionView.as_view(), name='metadata-union'),
    path('metadata/set-difference/', api.views.MetadataSetDifferenceView.as_view(), name='metadata-difference'),

    # Resources that are associated with specific Operations (OperationResources)
    path('operation-resources/<uuid:operation_uuid>/', api.views.OperationResourceList.as_view(), name='operation-resource-list'),
    path('operation-resources/<uuid:operation_uuid>/<str:input_field>/', api.views.OperationResourceFieldList.as_view(), name='operation-resource-field-list'),
    
    ################# Views for Operations ############################
    path('operations/', api.views.OperationList.as_view(), name='operation-list'),
    path('operations/add/', api.views.OperationCreate.as_view(), name='operation-create'),
    path('operations/<uuid:operation_uuid>/', api.views.OperationDetail.as_view(), name='operation-detail'),
    path('operations/<uuid:pk>/update/', api.views.OperationUpdate.as_view(), name='operation-update'),
    path('operations/run/', api.views.OperationRun.as_view(), name='operation-run'),
    path('executed-operations/', api.views.ExecutedOperationList.as_view(), name='executed-operation-list'),
    path('non-workspace-executed-operations/', api.views.NonWorkspaceExecutedOperationList.as_view(), name='non-workspace-executed-operation-list'),
    path('executed-operations/workspace/<uuid:workspace_pk>/', api.views.WorkspaceExecutedOperationList.as_view(), name='workspace-executed-operation-list'),
    path('executed-operations/workspace/<uuid:workspace_pk>/tree/', api.views.WorkspaceTreeView.as_view(), name='executed-operation-tree'),
    path('executed-operations/workspace/<uuid:workspace_pk>/tree/save/', api.views.WorkspaceTreeSave.as_view(), name='executed-operation-tree-save'),
    path('executed-operations/<uuid:exec_op_uuid>/', api.views.ExecutedOperationCheck.as_view(), name='operation-check'),
    path('operation-categories/', api.views.OperationCategoryList.as_view(), name='operation-category-list'),
    path('operation-categories/<str:category>/', api.views.OperationCategoryDetail.as_view(), name='operation-category-detail'),
    path('operation-categories-add/', api.views.OperationCategoryAdd.as_view(), name='operation-category-add'),

    ################# Views for public datasets ############################
    path('public-datasets/', api.views.PublicDatasetList.as_view(), name='public-dataset-list'),
    path('public-datasets/add/<str:dataset_id>/', api.views.PublicDatasetAdd.as_view(), name='public-dataset-create'),
    path('public-datasets/query/<str:dataset_id>/', api.views.PublicDatasetQuery.as_view(), name='public-dataset-query'),

    path('', api.views.ApiRoot.as_view(), name='api-root')
]

# add a path for checking that Sentry tracking is integrated
if settings.USING_SENTRY:
    urlpatterns.append(
        path('sentry-debug/', api.views.sentry_debug, name='sentry-debug')
    )