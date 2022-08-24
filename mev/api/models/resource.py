import uuid
import os

from django.contrib.auth import get_user_model
from django.db import models

from api.models.abstract_resource import AbstractResource
from api.models import Workspace


def upload_base(instance, path):
    '''
    This function can be passed to the `upload_to`
    kwarg of the django.db.models.FileField constructor.

    It allows us to save files to owner-specific directories
    relative to the settings.MEDIA_ROOT dir.
    '''
    return os.path.join(str(instance.owner.pk), path)


class Resource(AbstractResource):
    '''
    A `Resource` is an abstraction of data.  It represents some 
    piece of data we are analyzing or manipulating in the course of
    an analysis workflow.  

    `Resource`s are most often represented by flat files, but their 
    physical storage is not important.  They could be stored locally
    or in cloud storage accessible to MEV.  

    Various "types" of `Resource`s implement specific constraints
    on the data that are important for tracking inputs and outputs of
    analyses.  For example, if an analysis module needs to operate on
    a matrix of integers, we can enforce that the only `Resource`s 
    available as inputs are those identified (and verified) as 
    `IntegerMatrix` "types".  

    Note that we store all types of `Resource`s in the database as 
    a single table and maintain the notion of "type" by a 
    string-field identifier.  Creating specific database tables for
    each type of `Resource` would be unnecessary.  By connecting the
    string stored in the database with a concrete implementation class
    we can check the type of the `Resource`.

    `Resource`s are not active (`is_active` flag in the database) until their "type"
    has been verified.  API users will submit the intended type with
    the request and the backend will check that.  Violations are 
    reported and the `Resource` remains inactive (`is_active=False`). 
    '''

    # Some status messages to be displayed.
    UPLOADING = 'Uploading...'
    VALIDATING = 'Validating...'
    PROCESSING = 'Processing...'
    READY = ''
    UNABLE_TO_VALIDATE = 'Could not validate the resource given the information provided.'
    FAILED = 'Failed validation for resource type "{requested_resource_type}".'
    REVERTED = 'Reverting back to the previously valid state'
    UNKNOWN_RESOURCE_TYPE_ERROR = ('The requested resource type'
        ' of {requested_resource_type} is not a known type.')
    UNKNOWN_FORMAT_ERROR = ('File format "{fmt}" is not consistent'
        ' with the requested resource type ({readable_resource_type}).'
        ' Acceptable formats/extensions are: {extensions_csv}')
    UNEXPECTED_VALIDATION_ERROR = 'There was an unexpected error during validation. An administrator has been notified.'
    UNEXPECTED_STORAGE_ERROR = 'An unexpected error occurred during upload and storage. An administrator has been notified.'
    ERROR_WITH_REASON = 'An error ocurred: {ex}'

    # the name of the directory (relative to the storage root) where we will store
    # resources/files that are associated with MEV users
    USER_RESOURCE_STORAGE_DIRNAME = 'user_resources'

    # the name of the directory (relative to the storage root) where we will store
    # resources/files that are NOT associated with MEV users (but not those that
    # are operation resources). This covers the case where a Resource does not have
    # an owner
    OTHER_RESOURCE_STORAGE_DIRNAME = 'other_resources'

    # Resources are owned by someone.
    owner = models.ForeignKey(
        get_user_model(), 
        related_name = 'resources', 
        on_delete = models.CASCADE,
        blank = True,
        null = True
    )

    datafile = models.FileField(upload_to=upload_base, null=True)

    # Can attach a Resource to a Workspace, but 
    # this is not required.
    workspaces = models.ManyToManyField(
        Workspace,
        related_name = 'resources',
        blank = True
    )

    # A human-readable status (e.g. uploaded, processing, etc.)
    status = models.CharField(max_length=2000, 
        default='', 
        null=True, 
        blank=True
    )

    def save(self, *args, **kwargs):
        '''
        This overrides the save method, implementing
        custom behavior upon creation
        '''
        if self._state.adding:
            # If we wish, we can initially set the resource status to indicate
            # that there is some file validation checking (or otherwise)
            self.status = ''

        super().save(*args, **kwargs)


    def __str__(self):
        workspaces_str = ','.join([str(x.pk) for x in self.workspaces.all()])
        return '''Resource ({uuid})
          Name: {name}
          Owner: {owner}
          Workspaces: {workspaces}
          Created: {date}'''.format(
                name = self.name,
                uuid = str(self.id),
                owner = str(self.owner),
                workspaces = workspaces_str,
                date = self.creation_datetime
        )

