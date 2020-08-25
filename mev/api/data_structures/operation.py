import logging

from rest_framework.exceptions import ValidationError

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
        "inputs": Object<OperationInput>,
        "outputs": Object<OperationOutput>,
        "mode": <string>,
        "repository_url": <string url>,
        "git_hash": <string>
    }
    ```
    '''

    def __init__(self, id, name, description, inputs, outputs, mode, repository_url, git_hash):

        self.id = id
        self.name = name
        self.description = description
        self.inputs = inputs
        self.outputs = outputs
        self.mode = mode
        self.repository_url = repository_url
        self.git_hash = git_hash

    def __eq__(self, other):
        a = self.name == other.name
        b = self.description == other.description
        c = self.inputs == other.inputs
        d = self.outputs == other.outputs
        e = self.repository_url == other.repository_url
        f = self.git_hash == other.git_hash
        return all([a,b,c,d,e,f])