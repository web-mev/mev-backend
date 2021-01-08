from django.db import models

from api.models.abstract_resource import AbstractResource
from api.models import Operation

class OperationResource(AbstractResource):
    '''
    An `OperationResource` is a specialization of a `Resource`
    which is not owned by anyone specific, but is rather associated 
    with a single `Operation`. Used for things like genome indexes, etc.
    where the user is not responsible.

    Note that it maintains a reference to the `Operation` input field
    it should correspond to.
    '''

    # the name of the file (in the operation repository) which 
    # contains the paths to the operation resources
    OPERATION_RESOURCE_FILENAME = 'operation_resources.json'

    # the name of the directory(relative to the MEV storage "root")
    # where we will store the operation files. For instance,
    # <storage root>/operations/<operation_uuid>/<resource UUID>.<name>
    OPERATION_RESOURCE_DIRNAME = 'operation_resources'

    # which Operation does this Resource associate with...
    operation = models.ForeignKey(
        Operation,
        on_delete = models.CASCADE
    )

    # which input field does this resource belong to?
    input_field = models.CharField(
        max_length = 255,
        blank = False,
        null = False  
    )

    # override the default of setting a Resource to be inactive and private
    is_active = models.BooleanField(default=True)
    is_public = models.BooleanField(default=True)

    class Meta:
        # ensure that for every operation the input_field and name
        # are unique. Otherwise, one could apply a name which is not
        # unique for a given operation input
        unique_together = ('input_field', 'name', 'operation')