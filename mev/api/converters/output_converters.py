import os

from api.utilities.resource_utilities import validate_and_store_resource
from api.data_structures.attributes import DataResourceAttribute
from api.models import Resource

class BaseOutputConverter(object):

    def convert_output(self, job_id, workspace, output_spec, output_val):

        updated_output_val = None
        attribute_type = output_spec['attribute_type']
        if attribute_type == DataResourceAttribute.typename:
            # check if many
            # if many, deal with the list, otherwise, just a single path
            # TODO: take the path/s and create new Resource for the user
            # if only a single output, place into a list so we can handle
            # both single and multiple outputs in the same loop
            if output_spec['many'] == False:
                output_paths = [output_val,]
            else:
                output_paths = output_val

            # get the type of the DataResource:
            resource_type = output_spec['resource_type']

            # t
            resource_uuids = []
            for p in output_paths:
                # p is a path in the execution "sandbox" directory or bucket,
                # depending on the runner.
                # Create a new Resource and use the storage 
                # driver to send the file to its final location.

                # the "name"  of the file as the user will see it.
                name = '{id}.{n}'.format(
                    id = job_id,
                    n = os.path.basename(p)
                )

                resource = self.create_resource(workspace, p, name)
                validate_and_store_resource(resource, resource_type)
                resource_uuids.append(resource.pk)
            # now return the resource UUID(s) consistent with the 
            # output (e.g. if multiple, return list)
            if output_spec['many'] == False:
                return resource_uuids[0]
            else:
                return resource_uuids
            

class LocalOutputConverter(BaseOutputConverter):
    def create_resource(self, workspace, path, name):

        resource_instance = Resource.objects.create(
            owner = workspace.owner,
            workspace = workspace,
            path = path,
            name = name,
        )
        return resource_instance

class RemoteOutputConverter(BaseOutputConverter):
    pass

class LocalDockerOutputConverter(LocalOutputConverter):
    pass

class RemoteCromwellOutputConverter(RemoteOutputConverter):
    pass

