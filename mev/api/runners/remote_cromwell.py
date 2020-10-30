import os
import json
import datetime
import zipfile
import logging

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from api.runners.base import OperationRunner
from api.utilities.basic_utils import make_local_directory, \
    copy_local_resource
from api.runners.base import OperationRunner
from api.utilities.basic_utils import get_with_retry
from api.storage_backends import get_storage_backend
from api.cloud_backends import get_instance_region

logger = logging.getLogger(__name__)


class RemoteCromwellRunner(OperationRunner):
    '''
    Class that handles execution of `Operation`s using the WDL/Cromwell
    framework
    '''
    MODE = 'cromwell'
    NAME = settings.CROMWELL

    DOCKERFILE = 'Dockerfile'
    WDL_SUFFIX = 'wdl'
    MAIN_WDL = 'main.wdl'
    DEPENDENCIES_ZIPNAME = 'depenencies.zip'
    WDL_INPUTS = 'inputs.json'

    # Constants that are part of the payload submitted to Cromwell
    WORKFLOW_TYPE = 'WDL'
    WORKFLOW_TYPE_VERSION = 'draft-2'

    # API paths for the Cromwell server
    SUBMIT_ENDPOINT = '/api/workflows/v1'
    STATUS_ENDPOINT = '/api/workflows/v1/{cromwell_job_id}/status'
    OUTPUTS_ENDPOINT = '/api/workflows/v1/{cromwell_job_id}/outputs'
    METADATA_ENDPOINT = '/api/workflows/v1/{cromwell_job_id}/metadata'
    ABORT_ENDPOINT = '/api/workflows/v1/{cromwell_job_id}/abort'
    VERSION_ENDPOINT = '/engine/v1/version'

    # A list of files that are required to be part of the repository
    REQUIRED_FILES = OperationRunner.REQUIRED_FILES + [
        # need to define how to build the environment
        os.path.join(OperationRunner.DOCKER_DIR, DOCKERFILE),
        # the main "entrypoint" WDL
        MAIN_WDL,
        # the input json file, as a template
        WDL_INPUTS
    ]

    def __init__(self):
        self.read_cromwell_url()
        self.read_cromwell_bucket_name()
        
    def read_cromwell_url(self):
        try:
            self.CROMWELL_URL = os.environ['CROMWELL_SERVER_URL']
        except KeyError as ex:
            raise ImproperlyConfigured('To use the Cromwell runner, you must'
                ' set the "{k}" environment variable.'.format(
                    k = ex
                )
            )

    def read_cromwell_bucket_name(self):
        # check that the storage bucket exists-- since remote jobs require
        # the use of bucket storage, we can simply use the storage backend hook
        # to verify that the storage bucket exists in the same region as our
        # application
        try:
            self.CROMWELL_BUCKET = os.environ['CROMWELL_BUCKET']
        except KeyError as ex:
            raise ImproperlyConfigured('To use the Cromwell runner, you must'
                ' set the "CROMWELL_BUCKET" environment variable. Set it to the'
                ' name of the bucket, excluding any filesystem prefix like "gs://" or "s3://"'
            )

    def check_if_ready(self):
        '''
        Makes sure all the proper environment variables, etc. 
        are present to use this job runner. Should be invoked
        at startup of django app.
        '''

        # check that we can reach the Cromwell server
        url = self.CROMWELL_URL + self.VERSION_ENDPOINT
        response = get_with_retry(url)
        if response.status_code != 200:
            logger.info('The Cromwell server located at: {url}'
                ' was not ready.'.format(
                    url = url
                )
            )
            raise ImproperlyConfigured('Failed to reach Cromwell server.')

        bucket_region = get_storage_backend().get_bucket_region(self.CROMWELL_BUCKET)
        instance_region = get_instance_region()
        if bucket_region != instance_region:
            raise ImproperlyConfigured('The application is running on a'
                ' machine in the following region: {instance_region}. The'
                ' Cromwell bucket was found in {bucket_region}. They should'
                ' be located in the same region.'.format(
                    bucket_region = bucket_region,
                    instance_region = instance_region
                )
            )

    def _create_inputs_json(self, op_dir, validated_inputs, staging_dir):
        '''
        Takes the inputs (which are MEV-native data structures)
        and make them into something that we can inject into Cromwell's
        inputs.json format compatible with WDL

        For instance, this takes a DataResource (which is a UUID identifying
        the file), and turns it into a cloud-based path that Cromwell can access.
        '''
        # create/write the input JSON to a file in the staging location
        arg_dict = self._map_inputs(op_dir, validated_inputs)
        wdl_input_path = os.path.join(staging_dir, WDL_INPUTS)
        with open(wdl_input_path, 'w') as fout:
            json.dump(arg_dict, fout)

    def _copy_workflow_contents(self, op_dir, staging_dir):
        '''
        Copy over WDL files and other elements necessary to submit
        the job to Cromwell. Does not mean that we copy EVERYTHING
        in the op dir.

        Also creates zip archive of the "non main" WDL files, as required
        by Cromwell
        '''
        # copy WDL files over to staging:
        wdl_files = glob.glob(
            os.path.join(op_dir, '*.' + self.WDL)
        )
        for w in wdl_files:
            copy_local_resource(w, staging_dir)

        # if there are WDL files in addition to the main one, they need to be zipped
        # and submitted as 'dependencies'
        additional_wdl_files = [
            x for x in glob.glob(os.path.join(staging_dir, '*.' + self.WDL)) 
            if os.path.basename(x) != self.MAIN_WDL
        ]
        zip_archive = None
        if len(additional_wdl_files) > 0:
            zip_archive = os.path.join(staging_dir, self.DEPENDENCIES_ZIPNAME)
            with zipfile.ZipFile(zip_archive, 'w') as zipout:
                for f in additional_wdl_files:
                    zipout.write(f, os.path.basename(f))


    def send_job(self, staging_dir):

        # the path of the input json file:
        wdl_input_path = os.path.join(staging_dir, WDL_INPUTS)

        # pull together the components of the POST request to the Cromwell server
        submission_url = settings.CROMWELL_SERVER_URL + self.SUBMIT_ENDPOINT

        payload = {}
        payload = {'workflowType': config_dict['workflow_type'], \
            'workflowTypeVersion': config_dict['workflow_type_version']
        }

        # load the options file so we can fill-in the zones:
        options_json = {}
        current_zone = get_zone_as_string()
        if current_zone:
            options_json['default_runtime_attributes'] = {'zones': current_zone}

        options_json_str = json.dumps(options_json)
        options_io = io.BytesIO(options_json_str.encode('utf-8'))

        files = {
            'workflowOptions': options_io, 
            'workflowInputs': open(wdl_input_path,'rb')
        }
        
        if run_precheck:
            files['workflowSource'] = open(os.path.join(staging_dir, settings.PRECHECK_WDL), 'rb')
        else:
            files['workflowSource'] =  open(os.path.join(staging_dir, settings.MAIN_WDL), 'rb')

        zip_archive = os.path.join(staging_dir, ZIPNAME)
        if os.path.exists(zip_archive):
            files['workflowDependencies'] = open(zip_archive, 'rb')

        # start the job:
        try:
            response = requests.post(submission_url, data=payload, files=files)
        except Exception as ex:
            pass

    def run(self, executed_op, op_data, validated_inputs):
        logger.info('Running in remote Cromwell mode.')
        logger.info('Executed op type: %s' % type(executed_op))
        logger.info('Executed op ID: %s' % str(executed_op.id))
        logger.info('Op data: %s' % op_data)
        logger.info(validated_inputs)

        # the UUID identifying the execution of this operation:
        execution_uuid = str(executed_op.id)

        # get the operation dir so we can look at which converters to use:
        op_dir = os.path.join(
            settings.OPERATION_LIBRARY_DIR, 
            str(op_data['id'])
        )

        # create a sandbox directory where we will store the files:
        staging_dir = os.path.join(settings.OPERATION_EXECUTION_DIR, execution_uuid)
        make_local_directory(staging_dir)

        # create the Cromwell-compatible inputs.json from the user inputs
        self._create_inputs_json(op_dir, validated_inputs, staging_dir)

        # copy over the workflow contents:
        self._copy_workflow_contents(op_dir, staging_dir)

        # construct the request to the Cromwell server:
        self.send_job()