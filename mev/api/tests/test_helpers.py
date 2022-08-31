from io import BytesIO
import os
import resource

from django.core.files import File


def cleanup_resource_file(resource_instance):
    '''
    Clean up the file associated with the Resource, 
    not the db record. Recall that we needed to effectively
    copy the test files under our settings.MEDIA_ROOT to avoid
    raising SuspiciousOperation errors
    '''
    resource_instance.datafile.delete()

def associate_file_with_resource(resource_instance, filepath):
    '''
    This function is used to help when associating a REAL
    file with a Resource (or OperationResource) instance.

    Due to django's storage, if we try to use test files
    (located outside of settings.MEDIA_ROOT) during unit tests,
    django raises SuspiciousFileOperation errors. 

    This function acts as a single place where we can "copy"
    those files such that we are able to use them for unit tests
    '''
    with open(filepath, 'rb') as fin:
        file_contents = fin.read()

    # need to 'overwrite' any existing datafile attribute
    with BytesIO() as b:
        resource_instance.datafile = File(
            b, 
            os.path.basename(filepath)
        )
        resource_instance.save()

    # now write the file contents in there:
    with resource_instance.datafile.open('wb') as fout:
        fout.write(file_contents)
    