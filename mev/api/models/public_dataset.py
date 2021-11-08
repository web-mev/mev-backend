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

    # a JSON object which tracks the files pertaining to this 
    # public dataset. Each implementation class 
    # (e.g. in api.public_data.sources) knows how to deal with this
    # mapping
    file_mapping = models.JSONField(blank=True, null=True)

    # a JSON object which contains additional metadata about this dataset.
    # Since each dataset can be quite different, this field is a bit of an
    # "overflow" container for assisting with user interfaces, etc.
    # An example-- in the TCGA dataset, there are multiple cancer types identified
    # by a project code (e.g. "TCGA-LUAD"). A user might not familiar with this
    # naming scheme and we'd like to show "Lung adenocarcinoma". This field will
    # enable that sort of mapping
    additional_metadata = models.JSONField(blank=True, null=True)