from django.db import models

class PublicDataset(models.Model):
    '''
    A `PublicDataset` contains metadata about public data 
    repositories we expose through WebMeV
    '''

    # allows us to toggle visibility so that we can hide/unhide
    # public datasets
    active = models.BooleanField(default=False)

    # The "public" name, as might be shown in a UI
    public_name = models.CharField(max_length=100)

    # A description which explains the dataset
    description = models.TextField(blank=True, null=True)

    # A timestamp which tells us when the data was collected
    # We don't have an auto-add since we will update the record
    # when we pull newer data
    timestamp = models.DateField(blank=True, null=True)

    # A unique name for the dataset. This allows us
    # to, for example, construct the proper url to query solr (if
    # that is our indexing technology)
    index_name = models.CharField(max_length=30, unique=True)