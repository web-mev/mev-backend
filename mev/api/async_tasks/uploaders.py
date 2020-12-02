# from celery.decorators import task

# from api.uploaders import get_uploader_by_name

# @task(name='async_upload')
# def async_upload(job_id, uploader_name, user_pk, data):
#     uploader_type = get_uploader_by_name(uploader_name)
#     uploader = uploader_type()

#     # create an ExecutedOperation with the given job_id:

#     uploader.async_upload(user_pk, data)