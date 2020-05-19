from celery.decorators import task


@task(name='validate_resource')
def validate_resource(resource_pk):
    '''
    This function handles the background validation of uploaded
    files.  
    '''
    pass


