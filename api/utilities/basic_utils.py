import os
import errno

def make_local_directory(directory_path):
    '''
    A single location where we create directories and handle failures
    (hopefully) gracefully
    '''
    try:
        os.makedirs(directory_path)
    except FileExistsError as ex:
        if ex.errno == errno.EEXIST:
            #TODO log this.  Should not happen since
            # we previously checked that it did not exist.
            # However, not REALLY an error (could have been
            # caused by a race condition) 
            return 
        else:
            #TODO.  log this-- edge case
            raise ex
    except PermissionError as ex:
        if ex.errno == errno.EACCES:
            # could not create the directory due to permission issue.
            # Should not happen.  
            # TODO: Log
            pass
        raise ex

def move_resource(source, dest):
    '''
    Handles relocation of files from source to dest
    '''

    # check that the source actually exists:
    if not os.path.exists(source):
        # TODO: log that database is corrupted. 
        raise FileNotFoundError('No file exists at %s' % source)

    # check that the file does not already exist.
    # Since we prefix with a UUID, this is VERY unlikely
    # but we still check.
    # Given the fact that it's nigh impossible, we simply
    # pre-pend an integer until it becomes unique.
    # e.g. if /a/b.txt exists, we try /a/0b.txt.
    # if THAT exists, we try /a/10b.txt, etc.
    i = 0
    while os.path.exists(dest):
        b = os.path.basename(dest)
        d = os.path.dirname(dest)
        b = '%d%s' % (i,b)
        dest = '%s/%s' % (d, b)
        i += 1

    try:
        os.rename(source, dest)
        return dest
    except FileExistsError as ex:
        if ex.errno == errno.EEXIST:
            #TODO log this.  Should not happen since
            # we previously checked that it did not exist 
            pass 
        else:
            #TODO.  log this-- edge case.  The file existed but
            # it raised some other type of errno
            pass

        # regardless, raise the exception to catch higher-up
        raise ex
    except PermissionError as ex:
        if ex.errno == errno.EACCES:
            # could not move the file due to permission issue.
            # Should not happen.  
            # TODO: Log and issue warning to admins.
            pass
        raise ex