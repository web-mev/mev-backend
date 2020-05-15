import uuid

from django.contrib.auth import get_user_model
from django.db import models

from api.models import Workspace
from api.resource_types import DATABASE_RESOURCE_TYPES

class Resource(models.Model):
    '''
    A `Resource` is an abstraction of data files.  It represents some 
    piece of data we are analyzing or manipulating in the course of
    an analysis workflow.  

    `Resource`s are most often represented by flat files, but their 
    physical storage is not important.  They could be stored locally
    or in cloud storage accessible to MEV  

    Various "types" of `Resource`s implement specific constraints
    on the data that are important for tracking inputs and outputs of
    analyses.  For example, if an analysis module needs to operate on
    a matrix of integers, we can enforce that the only `Resource`s 
    available as inputs are those identified (and verified) as 
    `IntegerMatrix` "types".  

    Note that we store all types of `Resource`s in the database as 
    a single table and maintain the notion of "type" by a 
    string-field identifier.  Creating specific database tables for
    each type of `Resource` would be unnecessary.

    `Resource`s are not entered into the database until their "type"
    has been verified.  API users will submit the intended type with
    the request and the backend will check that.  Violations are 
    reported as errors and the `Resource` is not added to the database.

    Some additional notes:
    - `Resource`s are owned by users and *can* be added to a `Workspace`.  
    However, that is not required-- `Resource`s can be "unattached".  
    - When a `Resource` is added to a `Workspace`, a new copy is made.  This
    maintains the state of the original `Resource`.  In this way, the same 
    original file can be added to multiple `Workspace`s but users do not have
    to worry that modifications in one `Workspace` will affect those in other 
    `Workspace`s.  
    - `Resource`s can be made "public" so that others can view and import 
    them.  Once another user chooses to import the file, a copy is made and
    that new user has their own copy.    
    '''

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

    # the location of the file
    path = models.CharField(
        max_length = 255,
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

    # the "type" of the Resource.  Each type will have
    # characteristics that need to be verified.  For example
    # an integer matrix obviously can only contain integers.
    # These types will determine whether a file is acceptable
    # as an input to various analyses.
    resource_type = models.CharField(
        choices = DATABASE_RESOURCE_TYPES, 
        max_length = 5
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

