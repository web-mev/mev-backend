import sys
import os
from collections import UserDict

from django.core.management.base import BaseCommand
from django.conf import settings

from mkdocs.__main__ import cli
from mkdocs import config as mkdocs_config
from mkdocs.commands import build, gh_deploy


class Command(BaseCommand):
    help = 'Builds documentation with mkdocs and optionally deploys to github pages'

    def add_arguments(self, parser):

        parser.add_argument(
            '--push',
            default=False,
            help='Use this flag if you want to push the docs to github.'
        )

        parser.add_argument(
            '--remote_name',
            default='origin',
            help='The name of the remote'
        )

        parser.add_argument(
            '--remote_branch',
            default='gh-pages',
            help='The branch on the remote'
        )
                
        parser.add_argument(
            '--message',
            help='Commit message'
        )

        parser.add_argument(
            '--site_dir',
            help='The location where the built static site files will be placed.'
        )

    def handle(self, *args, **options):

        if options['site_dir']:
            site_dir = options['site_dir']
        else:
            site_dir = os.path.join(os.path.dirname(settings.MAIN_DOC_YAML), 'site')

        kwargs = {'config_file': settings.MAIN_DOC_YAML, 'site_dir': site_dir}

        # build docs
        build.build(mkdocs_config.load_config(**kwargs), dirty=False)

        # add the information relevant for the commit/push
        kwargs['remote_name'] = options['remote_name']
        kwargs['remote_branch'] = options['remote_branch']

        # due to the way config info is accessed from within the mkdocs gh_deploy
        # function below, it needs both dict-like access and attribute-like access
        # UserDict fits that bill
        config = UserDict(kwargs)
        config.config_file_path = settings.MAIN_DOC_YAML

        if options['push']:
            gh_deploy.gh_deploy(config, message=options['message'])
