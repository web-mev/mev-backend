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
    path('resources/<uuid:pk>/preview/', api.views.ResourcePreview.as_view(), name='resource-preview'),
    path('resources/<uuid:pk>/metadata/', api.views.ResourceMetadataView.as_view(), name='resource-metadata-detail'),
    path('resources/<uuid:pk>/metadata/observations/', api.views.ResourceMetadataObservationsView.as_view(), name='resource-metadata-observations'),
    path('resources/<uuid:pk>/metadata/features/', api.views.ResourceMetadataFeaturesView.as_view(), name='resource-metadata-features'),
    path('resources/<uuid:pk>/metadata/parent/', api.views.ResourceMetadataParentOperationView.as_view(), name='resource-metadata-parent-operation'),
    path('resources/upload/', api.views.ServerLocalResourceUpload.as_view(), name='resource-upload'),
    path('resources/upload/progress', 
        api.views.ServerLocalResourceUploadProgress.as_view(), 
        name='resource-upload-progress'
    ),

    # For querying the available types of Resources:
    path('resource-types/', api.views.ResourceTypeList.as_view(), name='resource-type-list'),

    # Resources that are associated with specific Workspaces
    path('workspaces/<uuid:workspace_pk>/resources/', api.views.WorkspaceResourceList.as_view(), name='workspace-resource-list'),
    path('workspaces/<uuid:workspace_pk>/resources/add/', api.views.WorkspaceResourceAdd.as_view(), name='workspace-resource-add'),

    ################# Views for Operations ############################
    path('operations/', api.views.OperationList.as_view(), name='operation-list'),
    path('operations/<uuid:operation_uuid>/', api.views.OperationDetail.as_view(), name='operation-detail'),

    path('', api.views.ApiRoot.as_view(), name='api-root')
]

# add a path for checking that Sentry tracking is integrated
if settings.USING_SENTRY:
    urlpatterns.append(
        path('sentry-debug/', api.views.sentry_debug, name='sentry-debug')
    )