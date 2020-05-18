from django.urls import path

from rest_framework_simplejwt import views as jwt_views

import api.views

urlpatterns = [
    path('token/', jwt_views.TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', jwt_views.TokenRefreshView.as_view(), name='token_refresh'),

    ##########################################################################

    # views for querying User instances
    path('users/', api.views.UserList.as_view(), name='user-list'),
    path('users/<int:pk>/', api.views.UserDetail.as_view(), name='user-detail'),

    ##################### Views for Workspaces ###############################

    path('workspaces/', api.views.WorkspaceList.as_view(), name='workspace-list'),
    path('workspaces/<uuid:pk>/', api.views.WorkspaceDetail.as_view(), name='workspace-detail'),

    ##################### Views for Resources ################################

    # general endpoints for Resources, regardless of Workspace association
    path('resources/', api.views.ResourceList.as_view(), name='resource-list'),
    path('resources/<uuid:pk>/', api.views.ResourceDetail.as_view(), name='resource-detail'),
    path('resources/upload/', api.views.ResourceUpload.as_view(), name='resource-upload'),

    # Resources that are associated with specific Workspaces
    path('workspaces/<uuid:workspace_pk>/resources/', api.views.WorkspaceResourceList.as_view(), name='workspace-resource-list'),

    ################# Views for Resource metadata ############################

    path('', api.views.ApiRoot.as_view(), name='api-root')
]
