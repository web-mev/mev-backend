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

    def __init__(self, id, name, \
        description, inputs, outputs, \
        mode, repository_url, git_hash, repo_name, workspace_operation):

        self.id = id
        self.name = name
        self.description = description
        self.inputs = inputs
        self.outputs = outputs
        self.mode = mode
        self.repository_url = repository_url
        self.git_hash = git_hash
        self.repo_name = repo_name
        self.workspace_operation = workspace_operation

    def to_dict(self):
        return {
            'id': str(self.id),
            'name': self.name,
            'description': self.description,
            'repository_url': self.repository_url,
            'repo_name': self.repo_name,
            'mode': self.mode,
            'git_hash': self.git_hash,
            'inputs': self.inputs.to_dict(),
            'outputs': self.outputs.to_dict(),
            'workspace_operation': self.workspace_operation
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