import uuid

from django.contrib.auth import get_user_model
from django.db import models

from api.models.abstract_resource import AbstractResource
from api.models import Workspace
from resource_types import DATABASE_RESOURCE_TYPES

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

    Some additional notes:

    - `Resource`s are owned by users and *can* be added to a `Workspace`.  
    However, that is not required-- `Resource`s can be "unattached".  

    - Regular users (non-admins) can't create new `Resource` directly via the API.
    The only way they can create a `Resource` is indirectly by adding a new upload.

    - When a `Resource` is added to a `Workspace`, a new copy of the database
    record is made.  This maintains the state of the original `Resource`.   

    - `Resource`s can be made "public" so that others can view and import 
    them.  Once another user chooses to import the file, a copy is made and
    that new user has their own copy.  If a `Resource` is later made "private"
    then any files that have been "used" by others *cannot* be recalled.

    - `Resource`s can be removed from a `Workspace`, but only if they have not 
    been used for any analyses/operations. 

    - `Resource`s cannot be transferred from one `Workspace` to another, but
    they can be copied.

    - A change in the type of the `Resource` can be requested.  Until the 
    validation of that change is complete, the `Resource` is made private and
    inactive.

    - Admins can make essentially any change to `Resources`, including creation.
    However, they must be careful to maintain the integrity of the database
    and the files they point to.
    
    - In a request to create a `Resource` via the API, the `resource_type`
    field can be blank/null.  The type can be inferred from the path of the
    resource.  We can do this because only admins are allowed to create via the API
    and they should only generate such requests if the resource type can be 
    inferred (i.e. admins know not to give bad requests to the API...) 
    '''

    # Some status messages to be displayed.
    UPLOADING = 'Uploading...'
    VALIDATING = 'Validating...'
    PROCESSING = 'Processing...'
    READY = ''
    FAILED = 'Failed validation for resource type {requested_resource_type}'
    REVERTED = ('Failed validation for type "{requested_resource_type}".'
        ' Reverting back to the valid type of "{original_resource_type}".')
    UNKNOWN_EXTENSION_ERROR = ('File extension for file "{filename}" is not consistent'
        ' with the requested resource type ({readable_resource_type}).'
        ' Acceptable extensions are: {extensions_csv}')
    UNEXPECTED_VALIDATION_ERROR = 'There was an unexpected error during validation.'
    UNEXPECTED_STORAGE_ERROR = 'An unexpected error occurred during upload and storage.'
    ERROR_WITH_REASON = 'An error ocurred: {ex}'

    # Resources are owned by someone.
    owner = models.ForeignKey(
        get_user_model(), 
        related_name = 'resources', 
        on_delete = models.CASCADE,
        blank = True,
        null = True
    )

    # Can attach a Resource to a Workspace, but 
    # this is not required.
    workspaces = models.ManyToManyField(
        Workspace,
        related_name = 'resources',
        blank = True,
        null = True
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

            # TODO: get the initial "name" from the upload path or something?
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

