import os
import glob
import json
import datetime
import zipfile
import logging
import io

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from api.runners.base import OperationRunner
from api.utilities.operations import get_operation_instance_data
from api.utilities.basic_utils import make_local_directory, \
    copy_local_resource, \
    alert_admins
from api.runners.base import OperationRunner
from api.utilities.basic_utils import get_with_retry, post_with_retry
from api.utilities.wdl_utils import WDL_SUFFIX, \
    get_docker_images_in_repo, \
    edit_runtime_containers
from api.utilities.docker import build_docker_image, \
    login_to_dockerhub, \
    push_image_to_dockerhub
from api.storage_backends import get_storage_backend
from api.cloud_backends import get_instance_zone, get_instance_region
from api.converters.output_converters import RemoteCromwellOutputConverter
from api.models.executed_operation import ExecutedOperation

logger = logging.getLogger(__name__)


class RemoteCromwellRunner(OperationRunner):
    '''
    Class that handles execution of `Operation`s using the WDL/Cromwell
    framework
    '''
    MODE = 'cromwell'
    NAME = settings.CROMWELL

    DOCKERFILE = 'Dockerfile'
    MAIN_WDL = 'main.wdl'
    DEPENDENCIES_ZIPNAME = 'dependencies.zip'
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

    # Some other constants (often defined on the Cromwell side)
    CROMWELL_DATETIME_STR_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'
    SUBMITTED_STATUS = 'Submitted'
    SUCCEEDED_STATUS = 'Succeeded'
    FAILED_STATUS = 'Failed'
    OTHER_STATUS = 'unknown/other' # marker for other response strings.

    # A list of files that are required to be part of the repository
    REQUIRED_FILES = OperationRunner.REQUIRED_FILES + [
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

    def prepare_operation(self, operation_dir, repo_name, git_hash):

        # get a list of the docker images in all the WDL files
        docker_image_names = get_docker_images_in_repo(operation_dir)
        logger.info('Found the following image names among the'
            ' WDL files: {imgs}'.format(
                imgs = ', '.join(docker_image_names)
            )
        )

        # iterate through those, building the images
        name_mapping = {}
        for full_image_name in docker_image_names:
            # image name is something like 
            # <docker repo, e.g. docker.io>/<username>/<name>:<tag>
            split_full_name = full_image_name.split(':')
            if len(split_full_name) == 2: #if a tag is specified
                image_prefix, tag = split_full_name
            elif len(split_full_name) == 1: # if no tag
                image_prefix = split_full_name[0]
            else:
                logger.error('Could not properly handle the following docker'
                    ' image spec: {x}'.format(x = full_image_name)
                )
                raise Exception('Could not make sense of the docker'
                    ' image handle: {x}'.format(x=full_image_name)
                )
            image_split = image_prefix.split('/')
            if len(image_split) == 3:
                docker_repo, username, image_name = image_split
            elif len(image_split) == 2:
                username, image_name = image_split
            else:
                logger.error('Could not properly handle the following docker'
                    ' image spec: {x}'.format(x = full_image_name)
                )
                raise Exception('Could not make sense of the docker'
                    ' image handle: {x}'.format(x=full_image_name)
                )
            dockerfile_name = '{df}.{name}'.format(
                df = self.DOCKERFILE,
                name = image_name
            )
            dockerfile_path = os.path.join(
                operation_dir, 
                self.DOCKER_DIR, 
                dockerfile_name
            )
            if not os.path.exists(dockerfile_path):
                raise Exception('To create the Docker image for {img}, expected'
                    ' a Dockerfile at: {p}'.format(
                        p = dockerfile_path,
                        img = image_prefix
                    )
                )
            
            # to create unambiguous images, we take the "base" image name 
            # (e.g. docker.io/myuser/foo) and append a tag which is the
            # github commit hash
            # Noted that `image_prefix` does NOT include the repo (e.g. docker.io)
            # or the username. This allows us to keep our own images in case a 
            # developer submitted a workflow that used images associated with their
            # personal dockerhub account
            build_docker_image(image_name, 
                git_hash, 
                dockerfile_path, 
                os.path.join(operation_dir, self.DOCKER_DIR)
            )
            login_to_dockerhub()
            pushed_image_str = push_image_to_dockerhub(image_name, git_hash)
            name_mapping[full_image_name] = pushed_image_str

        # change the name of the image in the WDL file(s), saving them in-place:
        edit_runtime_containers(operation_dir, name_mapping)


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
        wdl_input_path = os.path.join(staging_dir, self.WDL_INPUTS)
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
            os.path.join(op_dir, '*' + WDL_SUFFIX)
        )
        for w in wdl_files:
            dest = os.path.join(staging_dir, os.path.basename(w))
            copy_local_resource(w, dest)

        # if there are WDL files in addition to the main one, they need to be zipped
        # and submitted as 'dependencies'
        additional_wdl_files = [
            x for x in glob.glob(os.path.join(staging_dir, '*' + WDL_SUFFIX)) 
            if os.path.basename(x) != self.MAIN_WDL
        ]
        zip_archive = None
        if len(additional_wdl_files) > 0:
            zip_archive = os.path.join(staging_dir, self.DEPENDENCIES_ZIPNAME)
            with zipfile.ZipFile(zip_archive, 'w') as zipout:
                for f in additional_wdl_files:
                    zipout.write(f, os.path.basename(f))


    def send_job(self, staging_dir, executed_op):

        # the path of the input json file:
        wdl_input_path = os.path.join(staging_dir, self.WDL_INPUTS)

        # pull together the components of the POST request to the Cromwell server
        submission_url = self.CROMWELL_URL + self.SUBMIT_ENDPOINT

        payload = {}
        payload = {'workflowType': self.WORKFLOW_TYPE, \
            'workflowTypeVersion': self.WORKFLOW_TYPE_VERSION
        }

        # load the options file so we can fill-in the zones:

        options_json = {}
        current_zone = get_instance_zone()
        options_json['default_runtime_attributes'] = {'zones': current_zone}
        options_json_str = json.dumps(options_json)
        options_io = io.BytesIO(options_json_str.encode('utf-8'))

        files = {
            'workflowOptions': options_io, 
            'workflowInputs': open(wdl_input_path,'rb'),
            'workflowSource': open(os.path.join(staging_dir, self.MAIN_WDL), 'rb')
        }

        zip_archive = os.path.join(staging_dir, self.DEPENDENCIES_ZIPNAME)
        if os.path.exists(zip_archive):
            files['workflowDependencies'] = open(zip_archive, 'rb')

        # start the job:
        try:
            response = post_with_retry(submission_url, data=payload, files=files)
        except Exception as ex:
            logger.info('Submitting job ({id}) to Cromwell failed.'
                ' Exception was: {ex}'.format(
                    ex = ex,
                    id = exec_op_id
                )
            )

        self.handle_submission_response(response, executed_op)

    def handle_submission_response(self, response, executed_op):
        response_json = json.loads(response.text)
        if response.status_code == 201:
            try:
                status = response_json['status']
            except KeyError as ex:
                status = 'Unknown'
            if status == self.SUBMITTED_STATUS:
                logger.info('Job was successfully submitted'
                    ' to Cromwell.'
                )
                # Cromwell assigns its own UUID to the job
                cromwell_job_id = response_json['id']
                executed_op.job_id = cromwell_job_id
                executed_op.execution_start_datetime = datetime.datetime.now()
            else:
                logger.info('Received an unexpected status'
                    ' from Cromwell following a 201'
                    ' response code: {status}'.format(
                        status = response_json['status']
                    )
                )
                executed_op.status = status

        else:
            logger.info('Received a response code of {rc} when submitting job'
                ' to the remote Cromwell runner.'.format(
                    rc = response.status_code
                )
            )
            alert_admins()
            executed_op.status = 'Not submitted. Try again later. Admins have been notified.'
        executed_op.save()

    def query_for_metadata(self, job_uuid):
        '''
        Calls out to the Cromwell server to get metadata about
        a job. See 
        https://cromwell.readthedocs.io/en/stable/api/RESTAPI/#get-workflow-and-call-level-metadata-for-a-specified-workflow
        '''
        endpoint = self.METADATA_ENDPOINT.format(cromwell_job_id=job_uuid)
        metadata_url = self.CROMWELL_URL + endpoint
        response = get_with_retry(metadata_url)
        bad_codes = [404, 400, 500]
        if response.status_code in bad_codes:
            logger.info('Request for Cromwell job metadata returned'
                ' a {code} status.'.format(code=response.status_code)
            )
        elif response.status_code == 200:
            response_json = json.loads(response.text)
            return response_json
        else:
            logging.info('Received an unexpected status code when querying'
                ' the metadata of a Cromwell job.'
            )
    def query_for_status(self, job_uuid):
        '''
        Performs the work of querying the Cromwell server.
        Returns either a dict (i.e. the response) or None, if 
        the response did not have the expected 200 status code.
        '''
        endpoint = self.STATUS_ENDPOINT.format(cromwell_job_id=job_uuid)
        status_url = self.CROMWELL_URL + endpoint
        response = get_with_retry(status_url)
        bad_codes = [404, 400, 500]
        if response.status_code in bad_codes:
            logger.info('Request for Cromwell job status returned'
                ' a {code} status.'.format(code=response.status_code)
            )
        elif response.status_code == 200:
            response_json = json.loads(response.text)
            return response_json
        else:
            logging.info('Received an unexpected status code when querying'
                ' the status of a Cromwell job.'
            )

    def _parse_status_response(self, response_json):
        status = response_json['status']
        if status == self.SUCCEEDED_STATUS:
            return self.SUCCEEDED_STATUS 
        elif status == self.FAILED_STATUS:
            return self.FAILED_STATUS
        return self.OTHER_STATUS 

    def check_status(self, job_uuid):
        '''
        Returns a bool indicating whether we know if the job is finished.
        Unexpected responses return False, which will essentially block
        other actions until admins can investigate.
        '''
        response_json = self.query_for_status(job_uuid)
        if response_json:
            status = self._parse_status_response(response_json)
            # the job is complete if it's marked as success of failure
            if (status == self.SUCCEEDED_STATUS) or (status == self.FAILED_STATUS):
                return True
        return False

    def handle_job_success(self, executed_op):

        job_id = executed_op.job_id
        job_metadata = self.query_for_metadata(job_id)
        try:
            end_time_str = job_metadata['end']
        except KeyError as ex:
            end_time = datetime.datetime.now()            
        else:
            end_time = datetime.datetime.strptime(
                end_time_str, 
                self.CROMWELL_DATETIME_STR_FORMAT
            )

        # get the job outputs
        # This is a mapping of the Cromwell output ID (e.g. Workflow.Variable)
        # to either a primitive (String, Number) or a filepath (in a bucket)
        try:
            outputs_dict = job_metadata['outputs']
        except KeyError as ex:
            outputs_dict = {}
            logger.info('The job metadata payload received from executed op ({op_id})'
                ' with Cromwell ID {cromwell_id} did not contain the "outputs"'
                ' key in the payload'.format(
                    cromwell_id = job_id,
                    op_id = executed_op.id
                )
            )
            alert_admins()

        # instantiate the output converter class which will take the job outputs
        # and create MEV-compatible data structures or resources:
        converter = RemoteCromwellOutputConverter()
        converted_outputs = self.convert_outputs(executed_op, converter, outputs_dict)

        # set fields on the executed op:
        executed_op.outputs = converted_outputs
        executed_op.execution_stop_datetime = end_time
        executed_op.job_failed = False
        executed_op.status = ExecutedOperation.COMPLETION_SUCCESS


    def handle_job_failure(self, executed_op):

        job_id = executed_op.job_id
        job_metadata = self.query_for_metadata(job_id)
        try:
            end_time_str = job_metadata['end']
        except KeyError as ex:
            end_time = datetime.datetime.now()            
        else:
            end_time = datetime.datetime.strptime(
                end_time_str, 
                self.CROMWELL_DATETIME_STR_FORMAT
            )

        failure_list = job_metadata['failures']
        failure_messages = set()
        for f in failure_list:
            failure_messages.add(f['message'])

        # set fields on the executed op:
        executed_op.error_messages = list(failure_messages)
        executed_op.execution_stop_datetime = end_time
        executed_op.job_failed = True
        executed_op.status = ExecutedOperation.COMPLETION_ERROR

    def handle_other_job_outcome(self, executed_op):
        executed_op.status = ('Experienced an unexpected response'
            ' when querying for the job status. Admins have been notified.'
        )
        alert_admins()

    def finalize(self, executed_op):
        '''
        Finishes up an ExecutedOperation. Does things like registering files 
        with a user, cleanup, etc.
        '''
        job_id = str(executed_op.job_id)
        status_json = self.query_for_status(job_id)
        if status_json:
            status = self._parse_status_response(status_json)
        else:
            status = None
        if status == self.SUCCEEDED_STATUS:
            self.handle_job_success(executed_op)
        elif status == self.FAILED_STATUS:
            self.handle_job_failure(executed_op)
        else:
            self.handle_other_job_outcome(executed_op)

        executed_op.is_finalizing = False
        executed_op.save()


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
        self.send_job(staging_dir, executed_op)