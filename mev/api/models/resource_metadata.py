from django.db import models
from django.contrib.postgres.fields import JSONField

from api.models import ExecutedOperation, Resource

class ResourceMetadata(models.Model):
    '''
    ResourceMetadata helps with coordinating Feature and Observation instances
    that are associated with a Resource.  For instance, an expression count 
    matrix has samples and genes which correspond to an ObservationSet (of samples)
    and a FeatureSet (of genes).

    Additionally, the metadata tracks the origin of file so that the source of the file
    can be determined.
    '''

    # clearly the metadata about a Resource has to be associated
    # with that Resource
    resource = models.OneToOneField(
        Resource,
        primary_key = True,
        on_delete = models.CASCADE
    )

    # the `parent_operation` references the Operation
    # that created the Resource.  None/null indicates that
    # the Resource did not originate from any MEV operations
    parent_operation = models.ForeignKey(
        ExecutedOperation, 
        on_delete = models.CASCADE, 
        blank = True,
        null = True
    )

    # The ObservationSet and FeatureSet associated with a Resource
    # are simply JSON fields which come directly from their serialized
    # representation
    observation_set = JSONField(blank = True,null = True)
    feature_set = JSONField(blank = True, null = True)

    def __str__(self):
        return '''ResourceMetadata
          Resource: {resource_pk}
          Parent Op: {parent_operation}
          Observations: {observation_set}
          Features: {feature_set}'''.format(
                resource_pk = self.resource.pk,
                observation_set = self.observation_set,
                feature_set = self.feature_set,
                parent_operation = self.parent_operation
        )
    