from celery.decorators import task

from api.uploaders import get_uploader_by_name

@task(name='async_upload')
def async_upload(uploader_name, user_pk, data):
    print(uploader_name)
    uploader_type = get_uploader_by_name(uploader_name)
    uploader = uploader_type()
    uploader.async_upload(user_pk, data)