import os
import logging

from django.contrib.auth import get_user_model
from rest_framework import serializers, exceptions

from api.models import Resource, Workspace
from api.utilities.resource_utilities import set_resource_to_inactive
from api.serializers.workspace import WorkspaceSerializer
import api.async_tasks.async_resource_tasks as api_tasks

from constants import DB_RESOURCE_KEY_TO_HUMAN_READABLE

logger = logging.getLogger(__name__)

class ResourceSerializer(serializers.ModelSerializer):

    # add a human-readable datetime which will be added to the serialized representation
    created = serializers.DateTimeField(
        source='creation_datetime', 
        read_only=True
    )

    # Rather than reporting a full nested representation, we just report
    # the owner as its unique email
    owner_email = serializers.EmailField(
        source='owner.email', 
        required=False, 
        allow_null=True
    )

    # we would like to display the nested representation of the workspaces that
    # a particular Resource is associated with:
    workspaces = WorkspaceSerializer(many=True, required=False, read_only=True)

    # See `get_readable_resource_type` method below.
    readable_resource_type = serializers.SerializerMethodField()

    class Meta:
        model = Resource
        fields = [
            'id',
            'name',
            'datafile',
            'file_format',
            'resource_type',
            'owner_email',
            'is_active',
            'is_public',
            'status',
            'workspaces',
            'created',
            'size',
            'readable_resource_type'
        ]

    def get_readable_resource_type(self, obj):
        '''
        This method is invoked by our use of serializers.SerializerMethodField 
        on the readble_resource_type field.

        This method creates an extra field to be used by any GUI 
        that will show a nicer human-readable resource type rather 
        than our coded, shorthand type strings (e.g. show 
        "Expression matrix" instead of "MTX")
        '''
        if obj.resource_type:
            return DB_RESOURCE_KEY_TO_HUMAN_READABLE[obj.resource_type]
        else:
            return None

    # @staticmethod
    # def parse_request_parameters(validated_data):
    #     '''
    #     This is a helper function to parse out the various 
    #     optional parameters from the request to create or
    #     edit a Resource
    #     '''
    #     id = validated_data.get('id', None)
    #     path = validated_data.get('path', '')
    #     name = validated_data.get('name', '')
    #     workspaces = validated_data.get('workspaces', None),
    #     file_format = validated_data.get('file_format', None)
    #     resource_type = validated_data.get('resource_type', None)
    #     is_public = validated_data.get('is_public', False)
    #     is_active = validated_data.get('is_active', False)
    #     status = validated_data.get('status', '')
    #     size = validated_data.get('size', 0)

    #     return {
    #         'id': id,
    #         'path': path,
    #         'name': name,
    #         'workspaces': workspaces, 
    #         'file_format': file_format,
    #         'resource_type': resource_type,
    #         'is_public' : is_public,
    #         'is_active' : is_active,
    #         'status': status,
    #         'size': size
    #     }

    def create(self, validated_data): 

        logger.info('Received validated data: %s' % validated_data)
        
        instance = super().create(validated_data)
        instance.name = os.path.basename(instance.datafile.name)
        instance.is_active = True
        instance.save()
        return instance

    def update(self, instance, validated_data):
        '''
        When a user updates a Resource, they can only do a few things--
        - change the name
        - change the format (i.e. should this be parsed as a CSV, TSV, etc?)
        - change the resource type (which triggers a type validation)
        '''

        logger.info('Received validated data: %s' % validated_data)

        # if we are performing validation, or some other action has 
        # set the resource "inactive", we cannot make changes.  Issue an error 
        if not instance.is_active:
            logger.info('Change was requested on inactive Resource %s' % instance)
            raise exceptions.ParseError('The requested Resource'
            ' is not currently activated, possibly due to pending'
            ' validation.  Please wait and try again.')

        try:
            requesting_user = validated_data['requesting_user']
        except KeyError as ex:
            logger.info('The "requesting_user" was not supplied to the update method.')
            raise ex

        # we could just ignore any data attempting to
        # change the owner of the Resource, but
        # we will explicitly reject any attempts.
        original_owner_email = instance.owner.email
        new_requested_owner = validated_data.get('owner', None)
        if new_requested_owner:
            new_owner_email = new_requested_owner['email']
            if original_owner_email != new_owner_email:
                raise exceptions.ParseError({'owner_email':'Cannot change the owner of a workspace.'})

        # Note that we cannot change the workspace with this method.
        # However, providing a workspace is not an error provided the 
        # workspace (if assigned) happens to be the same.
        # We could ignore requests to change the associated workspace, but it is
        # more helpful to issue a message.
        if validated_data.get('workspaces', None):
            logger.info('A change in Workspace was requested.  Rejecting this request.')
            raise exceptions.ParseError({'workspaces':'Cannot change the workspaces.'
                ' Use the API methods to add or remove from the respective Workspace(s).'}
            )

        # Change the name or keep the existing if it wasn't supplied.
        instance.name = validated_data.get('name', instance.name)

        # Save now so that we can save changes that don't require validation
        # and immediately reflect them.
        # To avoid saving potentially invalid resource_type and/or file_format
        # values, we DON'T trigger this save later.
        instance.save()

        # Set this flat to False at the start. If any of the parameters
        # should trigger a validation check, simply assign this flag to True
        change_requiring_validation = False

        # Check if there was a file format requested. If so, this should
        # trigger a validation event.
        new_file_format = validated_data.get('file_format', instance.file_format)        
        if (new_file_format is not None) and (new_file_format != instance.file_format):
            logger.info('A new file format was requested. Changing'
                ' resource {pk} from {orig} to {final}'.format(
                    pk = str(instance.pk),
                    orig = instance.file_format,
                    final = new_file_format
                ) 
            )
            change_requiring_validation = True

        # Now handle any requests to change the resource type
        new_resource_type = validated_data.get('resource_type', instance.resource_type)
        if (new_resource_type is not None) and (new_resource_type != instance.resource_type):
            # Until the validation is complete we simply change the status and save.  
            # Note that the resource_type has NOT changed yet.  
            # 
            # If the validation succeeds, then the `resource_type` and
            # that status will be changed.
            #
            # Also note that we change the status immediately since the async
            # task might lag and not be executed immediately.
            logger.info('A new resource type was requested. Changing'
                ' resource {pk} from {orig} to {final}'.format(
                    pk = str(instance.pk),
                    orig = instance.resource_type,
                    final = new_resource_type
                ) 
            )
            change_requiring_validation = True

        # if the `resource_type` was changed in the request, start
        # the validation process.  Since it is calling an async, we
        # have to pass the primary key instead of the instance.
        if change_requiring_validation:
            logger.info('Queueing validation for updating resource %s with type %s ' % 
                (str(instance.pk), new_resource_type)
            )
            set_resource_to_inactive(instance)
            instance.status = Resource.VALIDATING
            api_tasks.validate_resource.delay(
                instance.pk, 
                new_resource_type,
                new_file_format
            )
        return instance
        