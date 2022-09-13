import uuid
import os
import logging

from django.conf import settings
from rest_framework.exceptions import ValidationError

from api.models import Operation as OperationDbModel
from .base import LocalUpload, RemoteUpload
from api.utilities.operations import validate_operation_inputs

THIS_DIR = os.path.dirname(os.path.abspath(__file__))

logger = logging.getLogger(__name__)

# a key used to locate the proper uploader
DROPBOX = '__dbx__'

class DropboxUploadMixin(object):

    def validate(self, user, inputs):
        op = OperationDbModel.objects.get(pk=self.op_id)
        try:
            validated_inputs = validate_operation_inputs(user, inputs, op, None)
            logger.info('Validated inputs: {v}'.format(v=validated_inputs))
            dict_representation = {}
            for k,v in validated_inputs.items():
                if v:
                    dict_representation[k] = v.get_value()
            logger.info('dict representation of inputs: {d}'.format(d=dict_representation))
            return dict_representation
            
        except ValidationError as ex:
            # This is double-guarding as we *should be* properly mapping above.
            # typically, it is more likely that the function above will raise an 
            # exception if a client request had bad or missing keys. Since we control
            # everything here, it is unlikely this exception will be raised.
            logger.error('Failed to map the inputs provided by the Dropbox-payload'
                ' into inputs compatible with the GCP Dropbox uploader.'
            )
            raise ex

class DropboxLocalUpload(LocalUpload, DropboxUploadMixin):
    '''
    This handles Dropbox-specific behavior for files that are initially uploaded
    to the MEV server before going to the final storage backend
    '''

    # The directory containing the Operation components. Relative to the
    # directory of this file. The actual Operation will be executed from the 
    # files in the "final" operation dir, but this lets the ingestion script 
    # know where the source is.
    op_dir = os.path.join(THIS_DIR, 'local_dropbox_upload')

    def __init__(self):
        self.op_id = OperationDbModel.objects.filter(name='Dropbox upload app for local storage')\
            .latest('addition_datetime')
        super().__init__()


    def rename_inputs(self, user, data):
        '''
        Takes the data provided by the front-end, which looks like:
        ```
        [
            {
                'download_link': 'https://dropbox-url.com/foo.txt',
                'filename': 'foo.txt'
            },
            {
                'download_link': 'https://dropbox-url.com/bar.txt',
                'filename': 'bar.txt'
            }
        ]
        ```
        and reformats it into inputs for this local Dropbox upload, which looks like
        ```
        [
            {
                "dropbox_links": ["","",...],
                "filenames": ["","",...],
            }
        ]
        ```
        The calling function expects a list of objects, which is why the data is structured as 
        shown above. Each object results in a call
        to start an asycnrhonous process. To avoid issues with many containers and potential
        I/O problems, we execute the local uploads sequentially. Thus, we create a list with 
        only the single item.

        Note that this is different than the "input mapping" which takes place
        in the creation of the command which is actually run (e.g. a docker run cmd)
        '''
        remapped_inputs = []
        d = {
            'dropbox_links': [],
            'filenames': []
        }
        for item in data:
            link = item['download_link']
            name = item['filename']
            d['dropbox_links'].append(link)
            d['filenames'].append(name)

        # double-check to ensure that the data payload is structured properly
        # for the Docker-based process
        d = self.validate(user, d)
        # as mentioned above, we return a one-item list
        return [d,]


class DropboxGCPRemoteUpload(RemoteUpload, DropboxUploadMixin):
    '''
    This handles Dropbox-specific behavior for files that go directly to the 
    storage backend. Since we require google-specific behavior, we have a 
    GCP-specific class
    '''

    # The directory containing the Operation components. Relative to the
    # directory of this file. The actual Operation will be executed from the 
    # files in the "final" operation dir, but this lets the ingestion script 
    # know where the source is.
    op_dir = os.path.join(THIS_DIR, 'gcp_bucket_dropbox_upload')

    def __init__(self):
        self.op_id = OperationDbModel.objects.filter(name='Dropbox upload app for GCP')\
            .latest('addition_datetime')
        super().__init__()

    def rename_inputs(self, user, data):
        '''
        Takes the data provided by the front-end, which looks like:
        ```
        [
            {
                'download_link': 'https://dropbox-url.com/foo.txt',
                'filename': 'foo.txt'
            },
            {
                'download_link': 'https://dropbox-url.com/bar.txt',
                'filename': 'bar.txt'
            }
        ]
        ```
        and reformats it into inputs for this GCP-based remote Dropbox 
        upload, which looks like an array where each element is like:
        ```
        {
            "GCPDropboxUpload.dropbox_link": "",
            "GCPDropboxUpload.filename": "",
            "GCPDropboxUpload.bucketname": "",
            "GCPDropboxUpload.storage_root": "" 
        }
        ```

        Note that this is different than the "input mapping" which takes that
        dictionary above and creates the proper inputs.json for submission to
        the cromwell server. In this case, it's a trivial operation since they
        are the same thing.
        '''

        # In django-storages, this is the bucket where we store all user files.
        bucket_name = settings.MEDIA_ROOT

        input_template = {
            'GCPDropboxUpload.dropbox_link': '',
            'GCPDropboxUpload.filename': '',
            'GCPDropboxUpload.bucketname': bucket_name,
            'GCPDropboxUpload.storage_root': self.tmp_folder_name  
        }
        remapped_inputs = []
        for item in data:
            d = input_template.copy()
            link = item['download_link']
            name = item['filename']
            d['GCPDropboxUpload.dropbox_link'] = link
            d['GCPDropboxUpload.filename'] = name
            d = self.validate(user, d)
            remapped_inputs.append(d)
        return remapped_inputs


class DropboxAWSRemoteUpload(RemoteUpload, DropboxUploadMixin):
    '''
    This handles Dropbox-specific behavior for files that go directly to the 
    storage backend. Since we require AWS-specific behavior, we have an 
    AWS-specific class
    '''

    # The directory containing the Operation components. Relative to the
    # directory of this file. The actual Operation will be executed from the 
    # files in the "final" operation dir, but this lets the ingestion script 
    # know where the source is.
    op_dir = os.path.join(THIS_DIR, 'aws_bucket_dropbox_upload')

    def __init__(self):
        self.op_id = OperationDbModel.objects.filter(name='Dropbox upload app for AWS')\
            .latest('addition_datetime')
        super().__init__()

    def rename_inputs(self, user, data):
        '''
        Takes the data provided by the front-end, which looks like:
        ```
        [
            {
                'download_link': 'https://dropbox-url.com/foo.txt',
                'filename': 'foo.txt'
            },
            {
                'download_link': 'https://dropbox-url.com/bar.txt',
                'filename': 'bar.txt'
            }
        ]
        ```
        and reformats it into inputs for this AWS-based remote Dropbox 
        upload, which looks like an array where each element is like:
        ```
        {
            "AWSDropboxUpload.dropbox_link": "",
            "AWSDropboxUpload.filename": ""
        }
        ```

        Note that this is different than the "input mapping" which takes that
        dictionary above and creates the proper inputs.json for submission to
        the cromwell server. However, in this case, it's a trivial operation since they
        are the same thing.
        '''

        input_template = {
            'AWSDropboxUpload.dropbox_link': '',
            'AWSDropboxUpload.filename': ''
        }
        remapped_inputs = []
        for item in data:
            d = input_template.copy()
            link = item['download_link']
            name = item['filename']
            d['AWSDropboxUpload.dropbox_link'] = link
            d['AWSDropboxUpload.filename'] = name
            d = self.validate(user, d)
            remapped_inputs.append(d)
        return remapped_inputs