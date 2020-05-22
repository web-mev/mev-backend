import os
import errno
import logging

logger = logging.getLogger(__name__)

def make_local_directory(directory_path):
    '''
    A single location where we create directories and handle failures
    (hopefully) gracefully
    '''
    try:
        logger.info('Attempt to create directory at %s' % directory_path)
        os.makedirs(directory_path)
    except FileExistsError as ex:
        if ex.errno == errno.EEXIST:
            # Should not happen since
            # we previously checked that it did not exist.
            # However, not REALLY an error (could have been
            # caused by a race condition)
            logger.warning('Directory at %s already existed, but previously was'
                ' determined not to exist.  Possible result of race condition when'
                ' creating directories for the same user.' % directory_path
            )
            return 
        else:
            logger.error('A FileExistsError was raised when trying to create a'
                ' directory at %s.  However, the issue was not a simple case'
                ' where it already existed.  Error number was %d.' % (directory_path,
                ex.errno)
            )
            raise ex
    except PermissionError as ex:
        if ex.errno == errno.EACCES:
            # could not create the directory due to permission issue.
            # Should not happen.  
            logger.error('Could not create a directory at %s'
                ' due to permissions issues' % directory_path
            )
        raise ex

def move_resource(source, dest):
    '''
    Handles relocation of files from source to dest
    '''
    logger.info('Moving resource from %s to %s' % (source, dest))

    # check that the source actually exists:
    if not os.path.exists(source):
        logger.error('The file at %s did not exist.  This likely means'
        ' the database was corrupted.') 
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
        logger.info('There was already a file at %s.'
            ' Changing the destination filename.' % dest)
        b = os.path.basename(dest)
        d = os.path.dirname(dest)
        b = '%d%s' % (i,b)
        dest = '%s/%s' % (d, b)
        i += 1

    try:
        logger.info('Moving from %s to %s' % (source, dest))
        os.rename(source, dest)
        return dest
    except FileExistsError as ex:
        if ex.errno == errno.EEXIST:
            directory_listing = os.listdir(os.path.dirname(dest))
            logger.error('File existed at %s, despite just checking this.'
                ' Directory listing is: %s' % (dest, '\n'.join(directory_listing))
            ) 
        else:
            logger.error('Some other FileExistsError (%s) was raised'
                ' when moving the file.' % (ex.errno)) 

        # regardless, raise the exception to catch higher-up
        raise ex
    except PermissionError as ex:
        if ex.errno == errno.EACCES:
            # could not move the file due to permission issue.
            # Should not happen.  
            logger.error('Could not move file due to permissions issue.')
        raise ex