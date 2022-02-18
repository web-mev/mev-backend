import uuid

from django.db import models

from resource_types import DATABASE_RESOURCE_TYPES

class AbstractResource(models.Model):
    '''
    This is the base class which holds common fields for both the user-owned
    `Resource` model and the user-independent `OperationResource` model. 
    '''

    # Resource instances will be referenced by their UUID instead of a PK
    id = models.UUIDField(
        primary_key = True, 
        default = uuid.uuid4
    )

    # the location of the file.  Since the files can be added in
    # a multitude of ways (perhaps outside the API), we permit 
    # this field to be blank.  We later fill that in once we have
    # all the necessary resource information.
    path = models.CharField(
        max_length = 4096,
        default = ''  
    )

    # the name of the Resource.  Allows users to create
    # named files but have the backend keep track of it by
    # some unique path.  For instance, we may choose to save
    # a file by a UUID identifier, but the user can set a 
    # more "friendly" name
    name = models.CharField(
        max_length = 255,
        default = ''
    )

    # The size of the resource in bytes.
    # Converters will handle conversion to human-readable form
    size = models.BigIntegerField(default=0)


    # the "type" of the Resource.  Each type will have
    # characteristics that need to be verified.  For example
    # an integer matrix obviously can only contain integers.
    # These types will determine whether a file is acceptable
    # as an input to various analyses.
    resource_type = models.CharField(
        choices = DATABASE_RESOURCE_TYPES, 
        max_length = 25,
        null = True,
        blank = True
    )

    # whether the resource is active.  If a file was just uploaded
    # and it has not been validated, then it is not active.  Similarly
    # this allows for 
    is_active = models.BooleanField(default=False)

    # whether the Resource can be viewed by other users.  Users could
    # choose to make files public or private
    is_public = models.BooleanField(default=False)

    # When the resource was added
    creation_datetime = models.DateTimeField(
        auto_now_add = True
    )

    class Meta:
        abstract = True