import logging

from rest_framework import serializers

from api.models import PublicDataset

logger = logging.getLogger(__name__)

class PublicDatasetSerializer(serializers.ModelSerializer):

    # add a human-readable date
    created = serializers.DateField(
        source='timestamp', 
        format = '%B %d, %Y',
        read_only=True
    )

    class Meta:
        model = PublicDataset
        fields = [
            'id',
            'active',
            'public_name',
            'description',
            'created',
            'index_name',
            'additional_metadata'
        ]