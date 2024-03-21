from api.tests.base import BaseAPITestCase

from api.utilities.docker import check_image_name_validity
from api.container_registries.github_cr import GithubContainerRegistry
from api.container_registries.dockerhub_cr import DockerhubRegistry

class DockerUtilsTester(BaseAPITestCase):

    def test_check_image_name_validity(self):

        git_hash = 'abc123'
        repo_name = 'my-repo'
        
        # test a fully-qualified image stays the same. Even if it comes from another
        # source (here Dockerhub) the base image name (pca) does not match the 
        # repository name, we are OK since the image is tagged
        initial_image_name = 'ghcr.io/web-mev/pca:123'
        final_image_name = check_image_name_validity(initial_image_name, repo_name, git_hash)
        self.assertTrue(initial_image_name == final_image_name)

        # On the other hand, test that an untagged image from ANOTHER repo/source fails.
        # Here, the image name (pca) does not match `repo_name` and there is no tag, so
        # we NEED to specify it (in the nextflow file, etc.)
        initial_image_name = 'quay.io/samtools'
        with self.assertRaisesRegex(Exception, 'require a tag'):
            check_image_name_validity(initial_image_name, repo_name, git_hash)

        # here, the image name matches the repo AND has a tag. Good to go:
        initial_image_name = f'docker.io/web-mev/{repo_name}:some-tag'
        final_image_name = check_image_name_validity(initial_image_name, repo_name, git_hash)
        self.assertTrue(initial_image_name == final_image_name)

        # test that an untagged image that matches our repository has a tag appended.
        # This covers the typical case where we have a Docker image that is built
        # by github actions, etc. and hence we cannot have the git commit PRIOR TO
        # the actual commit
        initial_image_name = f'ghcr.io/web-mev/{repo_name}'
        # note that we set things up so that github container registry
        # (implied by ghcr.io) has our tagging set up like sha-<HASH>
        # To ensure the tests work correctly, we get the tag format by importing
        # the tag format. This way, if we change that in the future, we don't
        # have to fix this test.
        tag_format = GithubContainerRegistry.TAG_FORMAT
        final_tag = tag_format.format(hash=git_hash)
        final_image_name = check_image_name_validity(initial_image_name, repo_name, git_hash)
        expected_name = f'{initial_image_name}:{final_tag}'
        self.assertTrue(expected_name == final_image_name)

        # similar to the prior test, but using Dockerhub here
        initial_image_name = f'docker.io/web-mev/{repo_name}'
        # note that we set things up so that the image comes from
        # Dockerhub (implied by docker.io), which has our tagging set up like <HASH>
        # To ensure the tests work correctly, we get the tag format by importing
        # the tag format. This way, if we change that in the future, we don't
        # have to fix this test.
        tag_format = DockerhubRegistry.TAG_FORMAT
        final_tag = tag_format.format(hash=git_hash)
        final_image_name = check_image_name_validity(initial_image_name, repo_name, git_hash)
        expected_name = f'{initial_image_name}:{final_tag}'
        self.assertTrue(expected_name == final_image_name)

        # Testing the 'shorter' docker image names:
        initial_image_name = f'docker.io/ubuntu'
        with self.assertRaisesRegex(Exception, 'require a tag'):
            check_image_name_validity(initial_image_name, repo_name, git_hash)

        # shorter name with a tag. That's ok
        initial_image_name = 'docker.io/ubuntu:jammy'
        final_image_name = check_image_name_validity(initial_image_name, repo_name, git_hash)
        self.assertTrue(initial_image_name == final_image_name)