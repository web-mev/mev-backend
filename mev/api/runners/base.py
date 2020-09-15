import os

class MissingRequiredFileException(Exception):
    pass

class OperationRunner(object):
    '''
    A base class for classes which handle the execution of jobs/operations
    '''
    # A list of files that are required to be part of the repository
    REQUIRED_FILES = []

    def check_required_files(self, operation_dir):
        '''
        Checks that the files required for a particular run mode are, in fact,
        in the directory.

        `operation_dir` is a path (local) to a directory containing the files
        defining the Operation
        '''
        all_files = []
        for root, dirs, files in os.walk(operation_dir):
            for f in files:
                b=os.path.join(root, f)
                relpath = os.path.relpath(b, operation_dir)
                all_files.append(relpath)

        for f in self.REQUIRED_FILES:
            if not f in all_files:
                raise MissingRequiredFileException('Could not locate the'
                    ' required file ({f}) in the repository at {d}'.format(
                        f=f,
                        d=operation_dir
                    )
                )