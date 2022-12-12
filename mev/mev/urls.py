
from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse

def root_page(request):
    return HttpResponse('The API is located at /api/')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('api-auth/', include('rest_framework.urls')),
    path('', root_page),
]

