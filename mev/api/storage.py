from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings

class S3ResourceStorage(S3Boto3Storage):
    bucket_name = settings.MEDIA_ROOT