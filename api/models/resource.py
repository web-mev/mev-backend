import uuid

from django.contrib.auth import get_user_model
from django.db import models

from api.models import Workspace
from resource_types import DATABASE_RESOURCE_TYPES

class Resource(models.Model):
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
    READY = ''
    FAILED = 'Failed validation for resource type {requested_resource_type}'
    REVERTED = ('Failed validation for type {requested_resource_type}.'
        ' Reverting back to the valid type of {original_resource_type}')
    UNEXPECTED_ERROR = 'There was an unexpected error during validation.'

    # Resource instances will be referenced by their UUID instead of a PK
    id = models.UUIDField(
        primary_key = True, 
        default = uuid.uuid4, 
        editable = False
    )

    # Resources are owned by someone.
    owner = models.ForeignKey(
        get_user_model(), 
        related_name = 'resources', 
        on_delete = models.CASCADE
    )

    # Can attach a Resource to a Workspace, but 
    # this is not required.
    workspace = models.ForeignKey(
        Workspace,
        related_name = 'workspace_resources',
        blank = True,
        null = True,
        on_delete = models.CASCADE
    )

    # the location of the file.  Since the files can be added in
    # a multitude of ways (perhaps outside the API), we permit 
    # this field to be blank.  We later fill that in once we have
    # all the necessary resource information.
    path = models.CharField(
        max_length = 255,
        default = ''  
    )

    # Whether the Resource is located locally or in remote
    # storage (e.g. a bucket)
    is_local = models.BooleanField(default=True)

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
        max_length = 5,
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

    # A human-readable status (e.g. uploaded, processing, etc.)
    status = models.CharField(max_length=255, 
        default='', 
        null=True, 
        blank=True
    )

    # When the resource was added
    creation_datetime = models.DateTimeField(
        auto_now_add = True
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
        workspace_str = str(self.workspace.pk) if self.workspace else 'None'
        return '''Resource ({uuid})
          Name: {name}
          Owner: {owner}
          Workspace: {workspace}
          Created: {date}'''.format(
                name = self.name,
                uuid = str(self.id),
                owner = str(self.owner),
                workspace = workspace_str,
                date = self.creation_datetime
        )

