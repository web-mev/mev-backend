from .local_docker import LocalDockerRunner
from .remote_cromwell import RemoteCromwellRunner

AVAILABLE_RUN_MODES = [
    LocalDockerRunner.MODE,
    RemoteCromwellRunner.MODE
]