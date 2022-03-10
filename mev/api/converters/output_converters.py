import os
import logging

from rest_framework.exceptions import ValidationError

from api.utilities.resource_utilities import validate_and_store_resource, \
    delete_resource_by_pk
from api.data_structures.attributes import DataResourceAttribute, \
    VariableDataResourceAttribute
from api.exceptions import StorageException
from api.models import Resource, ResourceMetadata
from api.exceptions import OutputConversionException
from api.data_structures.submitted_input_or_output import submitted_operation_input_or_output_mapping

logger = logging.getLogger(__name__)

class BaseOutputConverter(object):

    def convert_output(self, executed_op, workspace, output_definition, output_val):
        '''
        Converts the output payload from an ExecutedOperation into something
        that WebMEV can work with.

        Note that the `workspace` arg can be None if the ExecutedOperation was
        not associated with any Workspace (As would be the case for an upload
        performed by a job runner)
        '''
        # is this output actually required? Some jobs may have optional outputs
        # and a failure to locate the corresponding output is NOT a failure.
        output_required = output_definition['required']

        # the specification- what kind of output data do we expect?
        output_spec = output_definition['spec']
        attribute_type = output_spec['attribute_type']
        if attribute_type == DataResourceAttribute.typename:
            # check if many
            # if many, deal with the list, otherwise, just a single path
            # if only a single output, place into a list so we can handle
            # both single and multiple outputs in the same loop
            if output_spec['many'] == False:
                output_paths = [output_val,]
            else:
                output_paths = output_val

            # get the type of the DataResource:
            resource_type = output_spec['resource_type']

            resource_uuids = []
            for p in output_paths:
                logger.info('Converting path at: {p} to a user-associated resource.'.format(
                    p = p
                ))
                # p is a path in the execution "sandbox" directory or bucket,
                # depending on the runner.

                try:
                    new_resource_uuid = self.attempt_resource_addition(
                        executed_op, workspace, p, resource_type, output_required
                    )
                    resource_uuids.append(new_resource_uuid)
                except Exception as ex:
                    # cleanup
                    self.cleanup(resource_uuids)
                    # finally raise this exception which will trigger cleanup of any
                    # other outputs for this ExecutedOperation
                    raise OutputConversionException('')

            # now return the resource UUID(s) consistent with the 
            # output (e.g. if multiple, return list)
            if output_spec['many'] == False:
                return resource_uuids[0]
            else:
                return resource_uuids

        elif attribute_type == VariableDataResourceAttribute.typename:

            # in the case of a VariableDataResource output, we don't just get a
            # string or list of strings. We get an object or a list of objects.
            # Each of those objects has the path and the resource type.

            # check if many
            # if many, deal with the list, otherwise, just a single object
            # if only a single output, place into a list so we can handle
            # both single and multiple outputs in the same loop
            if output_spec['many'] == False:
                if not type(output_val) is dict:
                    raise OutputConversionException('For a VariableResourceType, we expect'
                        ' that the output format is provided as an object/dict.'
                        ' The value received was {v}'.format(v=output_val)
                    )
                output_objs = [output_val,]
            else:
                if not type(output_val) is list:
                    raise OutputConversionException('When there are multiple outputs, we expect a list.')
                for x in output_val:
                    if not type(x) is dict:
                        raise OutputConversionException('For a VariableResourceType, we expect'
                            ' that the output format is a list of objects/dicts.'
                            ' The value received was {v}'.format(v=output_val)
                        )
                output_objs = output_val

            # get the potential types of the VariableDataResource:
            potential_resource_types = output_spec['resource_types']

            resource_uuids = []
            for obj in output_objs:
                try:
                    p = obj['path']
                    resource_type = obj['resource_type']
                except KeyError as ex:
                    raise OutputConversionException('In the output object ({v}), we expect the'
                        ' following key: {k}'.format(
                            v = obj,
                            k = str(ex)
                        )
                    )

                # Before going any further, check the resource_type and that it's permitted
                if not resource_type in potential_resource_types:

                    # Delete any other resources since we don't want "incomplete" outputs
                    self.cleanup(resource_uuids)

                    raise OutputConversionException('The specified resource type of {rt}'
                        ' was not consistent with the permitted types of {t}'.format(
                            rt = resource_type,
                            t = ','.join(potential_resource_types)
                        )
                    )

                logger.info('Converting path at: {p} to a user-associated resource.'.format(
                    p = p
                ))
                # p is a path in the execution "sandbox" directory or bucket,
                # depending on the runner.

                try:
                    new_resource_uuid = self.attempt_resource_addition(
                        executed_op, workspace, p, resource_type, output_required
                    )                    
                    resource_uuids.append(new_resource_uuid)
                except Exception as ex:
                    # cleanup
                    self.cleanup(resource_uuids)
                    # finally raise this exception which will trigger cleanup of any
                    # other outputs for this ExecutedOperation
                    raise OutputConversionException('')

            # now return the resource UUID(s) consistent with the 
            # output (e.g. if multiple, return list)
            if output_spec['many'] == False:
                return resource_uuids[0]
            else:
                return resource_uuids
        else:
            # if we are here, then we have something other than a file-like output.
            attribute_typename = output_spec['attribute_type']
            try:
                output_class = submitted_operation_input_or_output_mapping[attribute_typename]
            except KeyError as ex:
                logger.error('Could not find an appropriate class for handling the output'
                    ' for the typename of {t}'.format(
                        t=attribute_typename
                    )
                )
                raise Exception('Could not find an appropriate class for typename {t}'
                    ' for output.'.format(
                        t = attribute_typename
                    )
                )
            logger.info('Check supplied output: {d}'.format(d=output_val))
            try:
                o = output_class(executed_op.owner, 
                    executed_op.operation, 
                    workspace, '', output_val, output_spec)
                return o.get_value()
            except ValidationError as ex:
                raise OutputConversionException(str(ex))

    def cleanup(self, resource_uuids):
        # also delete other Resources associated with this output key
        [delete_resource_by_pk(x) for x in resource_uuids]

    def create_output_filename(self, path, job_name):
        if len(job_name) > 0:
            return '{job_name}.{n}'.format(
                job_name = str(job_name),
                n = os.path.basename(path)
            )
        else:
            return os.path.basename(path)

    def attempt_resource_addition(self, executed_op, \
        workspace, path, resource_type, output_required):

        # the "name"  of the file as the user will see it.
        name = self.create_output_filename(path, executed_op.job_name) 

        # create the resource in the db.
        resource = self.create_resource(executed_op.owner, \
            workspace, path, name, output_required)

        # Now attempt to validate and store the resource. IF this succeeds,
        # then the resource will be moved to its final location and the resource_type
        # field will be set.
        # If there is an unrecoverable failure, this method will raise
        # an exception that is caught in the calling method
        try:
            validate_and_store_resource(resource, resource_type)
        except StorageException as ex:
            logger.info('Failed to store the resource.')
            # This gives us an opportunity to handle runner-specific
            # failures if desired.
            self.handle_storage_failure(resource, output_required)

            # if handle_storage_failure does not raise an 
            # exception, then it was "ok" that this file
            # did not store correctly (as in the case of 
            # optional outputs)
            return None

        # if the `validate_and_store` method failed to validate the 
        # resource type for some reason, then 
        # the resource_type attribute will not match the desired type.
        # That's a problem and we need to "roll back" both the current
        # Resource and any others created as part of this output (in the
        # case where an output produces multiple outputs/Resources)
        if resource.resource_type != resource_type:
            self.handle_invalid_resource_type(resource)
            raise OutputConversionException('Failed to validate the expected'
                ' resource type'
            )
        else:
            # everything worked out correctly!
            # add the info about the parent operation to the resource metadata
            rm = ResourceMetadata.objects.get(resource=resource)
            rm.parent_operation = executed_op
            rm.save()
            return str(resource.pk)

    def handle_storage_failure(self, resource, output_required):
        '''
        Base method for dictating behavior if a resource fails to store.
        Note that this isn't used if an issue like fileystem corruption occurs
        and a general exception is raised. It's used in situations where the 
        failure is predictable and a custom exception is raised.

        One common instance where this can happen is with Cromwell-based
        jobs where outputs are optional. In that case, Cromwell still 
        produces a path to a non-existent file. The storage backend will
        raise an exception and this method will handle any actions to take

        This base method simply removes the resource and returns None
        '''

        # Regardless of whether the output was required, we
        # delete the database instance so we don't have corrupted
        # contents in the database
        resource.delete()
        if output_required:
            # output WAS required, but we failed to store. That's a problem
            raise OutputConversionException('A storage exception was '
                ' encountered when attempting to store a required output ')

    def handle_invalid_resource_type(self, resource):
        '''
        If a resource fails to validate to its expected type, then we delete
        that Resource and any others that were created for this particular
        output field. This prevents there from being partial outputs which may lead
        to confusion about a job's success.
        '''
        logger.info('The validation method did not set the resource type'
            ' which indicates that validation did not succeed. Hence, the'
            ' resource ({pk}) will be removed.'.format(pk=resource.pk)
        )            
        # delete the current Resource that failed
        # The cast to a str is not necessary, but makes unit testing slightly simpler
        delete_resource_by_pk(str(resource.pk))

    def create_resource(self, owner, workspace, path, name, output_required):
        logger.info('From executed operation outputs based on a local job,'
            ' create a resource at {p} with name {n}'.format(
                p = path,
                n = name
            )
        )
        resource_instance = Resource.objects.create(
            owner = owner,
            path = path,
            name = name
        )
        if workspace:
            resource_instance.workspaces.add(workspace)
        resource_instance.save()
        return resource_instance

class LocalOutputConverter(BaseOutputConverter):
    pass        

class RemoteOutputConverter(BaseOutputConverter):
    pass

class LocalDockerOutputConverter(LocalOutputConverter):
    pass

class RemoteCromwellOutputConverter(RemoteOutputConverter):
    pass
