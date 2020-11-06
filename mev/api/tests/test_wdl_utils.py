import unittest
import unittest.mock as mock
import os
import shutil

from django.core.exceptions import ImproperlyConfigured

from api.tests.base import BaseAPITestCase

from api.utilities.wdl_utils import get_docker_images_in_repo, \
    parse_docker_runtime_declaration, \
    extract_docker_runtimes, \
    edit_runtime_containers

# the api/tests dir
TESTDIR = os.path.join(os.path.dirname(__file__), 'operation_test_files')
DEMO_TESTDIR = os.path.join(TESTDIR, 'demo_cromwell_workflow')

class WDLUtilsTester(BaseAPITestCase):

    def test_parse_runtime(self):
        '''
        Test that we get the expected docker image strings back.
        '''
        # a file with two docker images specified. One has a tag, the other does not.
        wdl_text = open(os.path.join(DEMO_TESTDIR, 'other1.wdl')).read()
        x = extract_docker_runtimes(wdl_text)
        expected_set = set(['docker.io/someUser/myImg:v0.0.2', 'docker.io/someUser/someImg'])
        self.assertEqual(x, expected_set)

        # this WDL has only a single, untagged image
        wdl_text = open(os.path.join(DEMO_TESTDIR, 'other2.wdl')).read()
        x = extract_docker_runtimes(wdl_text)
        self.assertEqual(x, set(['docker.io/someUser/anotherImg']))

    def test_parses_docker_images(self):
        images = get_docker_images_in_repo(DEMO_TESTDIR)
        expected_set = [
            'docker.io/someUser/myImg:v0.0.2', 
            'docker.io/someUser/someImg',
            'docker.io/someUser/anotherImg'
        ]
        self.assertCountEqual(images, expected_set)

    def test_wdl_docker_edits(self):
        tmpdir = os.path.join('/tmp', 'test_wdl')
        shutil.copytree(DEMO_TESTDIR, tmpdir)
        name_mapping = {
            'docker.io/someUser/myImg:v0.0.2':'docker.io/otherUser/myImg', 
            'docker.io/someUser/someImg':'docker.io/otherUser/someImg',
            'docker.io/someUser/anotherImg':'docker.io/otherUser/anotherImg'
        }

        edit_runtime_containers(tmpdir, name_mapping)

        # now parse the docker images in that directory to confirm they were changed:
        images = get_docker_images_in_repo(tmpdir)
        expected_set = [
            'docker.io/otherUser/myImg', 
            'docker.io/otherUser/someImg',
            'docker.io/otherUser/anotherImg'
        ]
        self.assertCountEqual(images, expected_set)
        shutil.rmtree(tmpdir)

    def test_spec_without_docker_repo(self):
        '''
        When we get the docker image name from the WDL file, we 
        should NOT have to specify the docker repository (e.g. docker.io)
        
        for example, we can simply write myUser/imgA instead of needing
        docker.io/myUser/imgA
        '''
        # a file with two docker images specified.
        # Neither have docker.io, but one has a tag and the other does not.
        wdl_text = open(os.path.join(TESTDIR, 'demo.wdl')).read()
        x = extract_docker_runtimes(wdl_text)
        expected_set = set(['someUser/myImg:v0.0.2', 'someUser/someImg'])
        self.assertEqual(x, expected_set)