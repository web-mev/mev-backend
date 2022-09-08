import uuid

from django.db import models
from django.core.exceptions import ValidationError
from django.core.files import File

from constants import DATABASE_RESOURCE_TYPES

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

    # the name of the Resource.  Allows users to create
    # named files but have the backend keep track of it by
    # some unique path.  For instance, we may choose to save
    # a file by a UUID identifier, but the user can set a 
    # more "friendly" name
    name = models.CharField(
        max_length = 255,
        default = ''
    )

    # This is a string that provides a cue for how to parse
    # a file. We only work with a set of "conventional" 
    # formats, but this field does not care about that.
    file_format = models.CharField(
        max_length = 25,
        blank = True,
        null = True
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

    def save(self, *args, **kwargs):
        '''
        This defines custom behavior to respect upon saving of a AbstractResource
        instance, including sub-classes.
        '''

        # a resource's type and format can either be completely unset 
        # (as it is when initially uploaded) or it needs to have BOTH fields set
        # (as would follow a successful validation process).
        # This custom save behavior blocks us from saving 'incomplete' states.
        resource_type_set = (self.resource_type is not None) and (len(self.resource_type) > 0)
        file_format_set = (self.file_format is not None) and (len(self.file_format) > 0)
        both_not_set = (not resource_type_set) and (not file_format_set)
        both_set = resource_type_set and file_format_set

        if both_not_set or both_set:
            super().save(*args, **kwargs)
        else:
            raise ValidationError('Attempting to set an incomplete state for the combination'
                ' of resource type and file format.'
            )

    def write_to_file(self, fh, file_basename):
        '''
        Used as a common way to write files and save to the 
        datafile member (a FileField).

        `fh` is a file-like object.
        `file_basename` is a string giving the basename
        of the file we are saving. The storage system will
        place it in the correct directory.
        '''
        self.datafile = File(fh, file_basename)
        self.save()

    class Meta:
        abstract = True