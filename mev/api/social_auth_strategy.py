from rest_social_auth.strategy import DRFStrategy
from django.http import JsonResponse
from django.conf import settings


class WebMeVAuthStrategy(DRFStrategy):
    
    def redirect(self, url):
        '''
        This override allows us to return a JSON payload
        rather than issuing a browser redirect as the 
        DjangoStrategy dictates
        '''
        return JsonResponse({
            'url': url
        })

    def build_absolute_uri(self, path=None):
        '''
        This override allows us to specify a redirect URI
        that is not from the domain hosting the backend. Redirects will
        be sent to the frontend application, not the backend.
        '''
        if self.request:
            provider = self.request.get_full_path().split('/')[-2]
            request_origin = self.request.META['HTTP_ORIGIN']
            return request_origin + settings.REST_SOCIAL_OAUTH_REDIRECT_URI + provider + '/'
        else:
            return path
