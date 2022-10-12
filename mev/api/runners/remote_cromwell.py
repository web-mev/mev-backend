import os
import glob
import json
import datetime
import zipfile
import logging

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from exceptions import OutputConversionException, \
    JobSubmissionException

from api.runners.base import OperationRunner
from api.utilities.basic_utils import make_local_directory, \
    copy_local_resource
from api.utilities.admin_utils import alert_admins
from api.runners.base import OperationRunner
from api.utilities.basic_utils import get_with_retry, post_with_retry
from api.utilities.wdl_utils import WDL_SUFFIX, \
    get_docker_images_in_repo, \
    edit_runtime_containers
from api.utilities.docker import check_image_exists, get_tag_format
from api.models.executed_operation import ExecutedOperation

logger = logging.getLogger(__name__)


class RemoteCromwellRunner(OperationRunner):
    '''
    Class that handles execution of `Operation`s using the WDL/Cromwell
    framework
    '''
    NAME = 'cromwell'

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

    def prepare_operation(self, operation_dir, repo_name, git_hash):

        # get a list of the docker images in all the WDL files
        # corresponding to this repo
        docker_image_names = get_docker_images_in_repo(operation_dir)
        logger.info('Found the following image names among the'
            ' WDL files: {imgs}'.format(
                imgs = ', '.join(docker_image_names)
            )
        )

        # We need to ensure the images are available from Cromwell's use.
        # There are a couple situations:
        # 1. an image is directly related to this repository (e.g. it is built
        #    off a Dockerfile.<repo name> which exists in the repo). In this case
        #    the image is NOT tagged with the commit hash in the WDL file since
        #    we don't have that commit hash until AFTER we make the commit. We
        #    obviously cannot know the tag in advance and provide that tag
        #    in the WDL file. In this case, we check that the image can be found
        #    (e.g. in github CR or dockerhub) and then edit the cloned WDL to tag
        #    it. IF the image does happen to have a tag, then we do NOT edit it.
        #    It is possible that a new commit may try to use an image built off a 
        #    previous commit. While that is not generally how we advise, it's not
        #    incorrect since we have an umambiguous container image reference.
        #
        # 2. An image is from external resources and hence NEEDS a tag. An example
        #    might be use of a samtools Docker. It would be unnecessary to create our
        #    own samtools docker. However, we need to unambiguously know which samtools
        #    container we ended up using.
        #
        # Below, we iterate through the Docker images and make these checks/edits
        name_mapping = {}
        for full_image_name in docker_image_names:
            # image name is something like 
            # ghcr.io/web-mev/pca:sha-abcde1234
            # in the format of <registry>/<org>/<name>:<tag>
            # (recall the tag does not need to exist)

            # First determine whether an image tag 
            # exists.
            split_full_name = full_image_name.split(':')
            if len(split_full_name) == 2: #if a tag is specified
                image_prefix, tag = split_full_name
                image_is_tagged = True
            elif len(split_full_name) == 1: # if no tag
                image_prefix = split_full_name[0]
                image_is_tagged = False
            else:
                logger.error('Could not properly handle the following docker'
                    ' image spec: {x}'.format(x = full_image_name)
                )
                raise Exception('Could not make sense of the docker'
                    ' image handle: {x}'.format(x=full_image_name)
                )
            
            # Look at the image string (the non-tag portion)
            image_split = image_prefix.split('/')
            if len(image_split) == 3:
                docker_repo, username, image_name = image_split
            else:
                err_msg = ('Could not properly handle the following docker'
                    ' image spec: {x}.\nBe sure to include the registry prefix'
                    ' and user/org account'.format(
                        x = full_image_name)
                )
                logger.error(err_msg )
                raise Exception(err_msg)

            # if the image_name matches the repo, then we are NOT expecting 
            # a tag (see above).
            # However, a tag may exist, in which case we will NOT edit that.
            if image_name == repo_name:
                if not image_is_tagged:
                    tag_format = get_tag_format(docker_repo)
                    tag = tag_format.format(hash = git_hash)
                    final_image_name = full_image_name + ':' + tag
                else:  # image WAS tagged and associated with this repo
                    final_image_name = full_image_name
            else:
                # the image is "external" to our repo, in which case it NEEDS a tag
                if not image_is_tagged:
                    raise Exception('Since the Docker image {img} had a name indicating it'
                        ' is external to the github repository, we require a tag. None'
                        ' was found.'.format(img = full_image_name)
                    )
                else: # was tagged AND "external"
                    final_image_name = full_image_name

            image_found = check_image_exists(final_image_name)
            if not image_found:
                raise Exception('Could not locate the following'
                    ' image: {img}. Aborting'.format(img = final_image_name))

            # keep track of any "edited" image names so we can modify
            # the WDL files
            name_mapping[full_image_name] = final_image_name

        # change the name of the image in the WDL file(s), saving them in-place:
        edit_runtime_containers(operation_dir, name_mapping)


    def check_if_ready(self):
        '''
        Makes sure all the proper environment variables, etc. 
        are present to use this job runner. Should be invoked
        at startup of django app.
        '''

        # check that we can reach the Cromwell server
        url = settings.CROMWELL_SERVER_URL + self.VERSION_ENDPOINT
        try:
            response = get_with_retry(url)
        except Exception as ex:
            logger.info('An exception was raised when checking if the remote Cromwell runner was ready.'
                ' The exception reads: {ex}'.format(ex=ex)
            )
            raise ImproperlyConfigured('Failed to check the remote Cromwell runner. See logs.')
        if response.status_code != 200:
            logger.info('The Cromwell server located at: {url}'
                ' was not ready.'.format(
                    url = url
                )
            )
            raise ImproperlyConfigured('Failed to reach Cromwell server.')

    def _create_inputs_json(self, op, op_dir, validated_inputs, staging_dir):
        '''
        Takes the inputs (which are MEV-native data structures)
        and make them into something that we can inject into Cromwell's
        inputs.json format compatible with WDL

        For instance, this takes a DataResource (which is a UUID identifying
        the file), and turns it into a cloud-based path that Cromwell can access.

        Note that `op` is an instance of data_structures.operation.Operation
        '''
        # create/write the input JSON to a file in the staging location
        arg_dict = self._convert_inputs(op, op_dir, validated_inputs, staging_dir)
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
        submission_url = settings.CROMWELL_SERVER_URL + self.SUBMIT_ENDPOINT

        payload = {}
        payload = {'workflowType': self.WORKFLOW_TYPE, \
            'workflowTypeVersion': self.WORKFLOW_TYPE_VERSION
        }

        files = {
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
            logger.info(f'Submitting job ({executed_op.id}) to Cromwell failed.'
                f' Exception was: {ex}')
            response = None
        self.handle_submission_response(response, executed_op)

    def handle_submission_response(self, response, executed_op):
        '''
        After trying to POST to cromwell, we end up here regardless.

        This method handles both expected and unexpected responses,
        as well as complete failures from the POST
        '''
        if response is not None:
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
                    message = ('Received an unexpected status'
                        ' from Cromwell following a 201'
                        f' response code: {status}')
                    logger.info(message)
                    self._handle_submission_issue(executed_op)
            else:
                message = ('Received an unexpected status code'
                    f' of {response.status_code} from Cromwell.')
                logger.info(message)
                self._handle_submission_issue(executed_op)
        else:
            # response was None, which is not expected. Could be due
            # to Cromwell going offline, etc.
            self._handle_submission_issue(executed_op)

        executed_op.save()

    def _handle_submission_issue(self, executed_op, status_message=None):
        '''
        Used to handle situations where the job submission did not go
        as expected (e.g. 201 response and expected payload).

        Sets the proper fields so that we don't end up with a hanging
        job
        '''
        if status_message is None:
            status_message = ('Unexpected issue with job submission.'
                    ' WebMeV admins have been notified.')
        # set a bunch of fields so that we aren't left with an
        # ambiguous state
        executed_op.execution_start_datetime = datetime.datetime.now()
        executed_op.execution_stop_datetime = datetime.datetime.now()
        executed_op.status = status_message
        executed_op.job_failed = True
        executed_op.save()
        alert_admins('There was an issue with job submission for executed'
            f' operation with id: {executed_op.id}')
        raise JobSubmissionException()

    def query_for_metadata(self, job_uuid):
        '''
        Calls out to the Cromwell server to get metadata about
        a job. See 
        https://cromwell.readthedocs.io/en/stable/api/RESTAPI/#get-workflow-and-call-level-metadata-for-a-specified-workflow
        '''
        endpoint = self.METADATA_ENDPOINT.format(cromwell_job_id=job_uuid)
        metadata_url = settings.CROMWELL_SERVER_URL + endpoint
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
        status_url = settings.CROMWELL_SERVER_URL + endpoint
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
        # if we have not returned, then we received a 400,404,500 or something
        # else unexpected. return None


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
        if response_json is not None:
            status = self._parse_status_response(response_json)
            # the job is complete if it's marked as success of failure
            if (status == self.SUCCEEDED_STATUS) or (status == self.FAILED_STATUS):
                return True
        return False

    def handle_job_success(self, executed_op, op):
        '''
        `op` is an instance of data_structures.operation.Operation
        '''

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
            error_msg = ('The job metadata payload received from'
                f' executed op ({executed_op.job_id})'
                f' with Cromwell ID {job_id} did not contain the'
                ' "outputs" key in the payload')
            logger.info(error_msg)
            alert_admins(error_msg)

        try:
            converted_outputs = self._convert_outputs(executed_op, op, outputs_dict)
            executed_op.outputs = converted_outputs
            executed_op.execution_stop_datetime = end_time
            executed_op.job_failed = False
            executed_op.status = ExecutedOperation.COMPLETION_SUCCESS
        except OutputConversionException as ex:
            executed_op.execution_stop_datetime = end_time
            executed_op.job_failed = True
            executed_op.status = ExecutedOperation.FINALIZING_ERROR
            alert_admins(str(ex)) 


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
        alert_admins(
            'Experienced an unexpected response when querying for '
            'the job status of op: {op_id}.'.format(op_id=executed_op.job_id)
        )

    def finalize(self, executed_op, op):
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
            self.handle_job_success(executed_op, op)
        elif status == self.FAILED_STATUS:
            self.handle_job_failure(executed_op)
        else:
            self.handle_other_job_outcome(executed_op)

        executed_op.is_finalizing = False
        executed_op.save()


    def run(self, executed_op, op, validated_inputs):
        logger.info('Running in remote Cromwell mode.')
        logger.info(f'Executed op type: {type(executed_op)}')
        logger.info(f'Executed op ID: {executed_op.id}')
        logger.info(f'Op data: {op.to_dict()}')
        logger.info(f'Validated inputs: {validated_inputs}')

        # the UUID identifying the execution of this operation:
        execution_uuid = str(executed_op.id)

        # get the operation dir so we can look at which converters to use:
        op_dir = os.path.join(
            settings.OPERATION_LIBRARY_DIR, 
            str(op.id)
        )

        # create a sandbox directory where we will store the files:
        staging_dir = self._create_execution_dir(execution_uuid)

        # create the Cromwell-compatible inputs.json from the user inputs
        self._create_inputs_json(op, op_dir, validated_inputs, staging_dir)

        # copy over the workflow contents:
        self._copy_workflow_contents(op_dir, staging_dir)

        # construct the request to the Cromwell server:
        self.send_job(staging_dir, executed_op)


    def cleanup_on_error(self, op_spec_outputs, converted_outputs_dict):
        '''
        If there is an error during conversion of the outputs, we don't want
        any Resource instances to be kept. For instance, if there are multiple
        output files created and one fails validation, we don't want to expose the
        others since it may cause a situation where the output state is ambiguous.

        `op_spec_outputs` is the "operation spec" from the `Operation` instance. That
        details what the expected output(s) should be.

        `converted_outputs_dict` is a dict that has outputs that have already been
        converted.
        '''
        pass