from rest_framework.schemas.openapi import AutoSchema

class SchemaMixin(AutoSchema):
    '''
    By default, the introspection does not work for APIView
    unless a get_serializer method is implemented.  Add this
    mixin class to any views that are not generating API
    schemas automatically.
    '''
    def get_serializer(self):
        return self.serializer_class()
