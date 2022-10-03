import logging
import uuid

from exceptions import DataStructureValidationException, \
    AttributeValueError 

from data_structures.attribute_types import BooleanAttribute
from data_structures.operation_input_output_dict import \
    OperationInputDict, \
    OperationOutputDict
logger = logging.getLogger(__name__)


class Operation(object):
    '''
    This class defines a data structure that holds information about
    an analysis

    An `Operation` contains the following:
    ```
    {
        "id": <UUID>,
        "name": <string>,
        "description": <string>,
        "inputs": <OperationInputDict>,
        "outputs": <OperationOutputDict>,
        "mode": <string>,
        "repository_url": <string url>,
        "git_hash": <string>,
        "repo_name": <string>,
        "workspace_operation": <bool>
    }
    ```
    '''

    ID_FIELD = 'id'
    NAME_FIELD = 'name'
    DESC_FIELD = 'description'
    MODE_FIELD = 'mode'
    REPO_URL_FIELD = 'repository_url'
    REPO_NAME_FIELD = 'repository_name'
    GIT_HASH_FIELD = 'git_hash'
    WORKSPACE_OP_FIELD = 'workspace_operation'
    INPUTS_FIELD = 'inputs'
    OUTPUTS_FIELD = 'outputs'
    REQUIRED_FIELDS = set([
        ID_FIELD,
        NAME_FIELD,
        DESC_FIELD,
        MODE_FIELD,
        REPO_URL_FIELD,
        REPO_NAME_FIELD,
        GIT_HASH_FIELD,
        WORKSPACE_OP_FIELD,
        INPUTS_FIELD,
        OUTPUTS_FIELD
    ])

    def __init__(self, submitted_dict):

        if not type(submitted_dict) is dict:
            raise DataStructureValidationException('The constructor for an'
                ' Operation expects a dictionary.')  

        submitted_keys = set(submitted_dict.keys())
        if not submitted_keys == self.REQUIRED_FIELDS:
            extra_keys = submitted_keys.difference(self.REQUIRED_FIELDS)
            missing_keys = self.REQUIRED_FIELDS.difference(submitted_keys)
            message = ('The set of fields in the submitted Operation did not'
                ' match the requirements. Please address the following:\n')
            if missing_keys:
                message += f'Missing keys: {",".join(missing_keys)}\n'
            if extra_keys:
                message += f'Extra keys: {",".join(extra_keys)}'
            raise DataStructureValidationException(message)

        # At this point we know we have the required keys
        # ID is required and we use a setter to validate it.
        self.id = submitted_dict['id']

        # these are nested structures which need to be validated:
        self.inputs = OperationInputDict(submitted_dict['inputs'])
        self.outputs = OperationOutputDict(submitted_dict['outputs'])

        # These other do not have any required structure
        self.name = submitted_dict[self.NAME_FIELD]
        self.description = submitted_dict[self.DESC_FIELD]
        self.mode = submitted_dict[self.MODE_FIELD]
        self.repository_url = submitted_dict[self.REPO_URL_FIELD]
        self.repo_name = submitted_dict[self.REPO_NAME_FIELD]
        self.git_hash = submitted_dict[self.GIT_HASH_FIELD]

        # needs to be a bool. Just use our BooleanAttribute as a 
        # way to validate that:
        b = BooleanAttribute(submitted_dict[self.WORKSPACE_OP_FIELD])
        self.workspace_operation = b.value

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, x):
        try:
            self._id = str(uuid.UUID(x))
        except ValueError:
            raise AttributeValueError(f'{x} was not a valid UUID.')

    def to_dict(self):
        return {
            self.ID_FIELD: str(self.id),
            self.NAME_FIELD: self.name,
            self.DESC_FIELD: self.description,
            self.REPO_URL_FIELD: self.repository_url,
            self.REPO_NAME_FIELD: self.repo_name,
            self.MODE_FIELD: self.mode,
            self.GIT_HASH_FIELD: self.git_hash,
            self.INPUTS_FIELD: self.inputs.to_dict(),
            self.OUTPUTS_FIELD: self.outputs.to_dict(),
            self.WORKSPACE_OP_FIELD: self.workspace_operation
        }

    def __eq__(self, other):
        a = self.name == other.name
        b = self.description == other.description
        c = self.inputs == other.inputs
        d = self.outputs == other.outputs
        e = self.repository_url == other.repository_url
        f = self.git_hash == other.git_hash
        g = self.repo_name == other.repo_name
        h = self.workspace_operation == other.workspace_operation
        return all([a,b,c,d,e,f,g,h])