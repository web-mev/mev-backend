from api.serializers import ResourceSerializer

def check_for_resource_operations(resource_instance):
    '''
    To prevent deleting critical resources, we check to see if a
    `Resource` instance has been used for any operations within a
    `Workspace`.  If it has, return True.  Otherwise return False.
    '''
    pass

def create_resource_from_upload(filepath, filename, resource_type, owner):
    '''
    Creates and returns a Resource instance.
    `filepath` is a path to the file-based resource.  Could be local or in bucket-based
    storage.
    `filename` is a string, extracted from the name of the uploaded file.
    `resource_type` is one of the acceptable resource type identifiers
    `owner` is an instance of our user model
    '''
    # create a serialized representation so we can use the validation
    # contained there
    d = {'owner_email': owner.email,
        'path': filepath,
        'name': filename,
        'resource_type': resource_type
    }
    rs = ResourceSerializer(data=d)

    # values were checked prior to this, but we enforce this again
    if rs.is_valid(raise_exception=True):
        r = rs.save()
        return r