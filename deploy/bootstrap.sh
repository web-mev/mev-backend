#!/usr/bin/env bash

# exit immediately on errors in any command
set -e
# print commands and their expanded arguments
set -x

CODENAME=$(/usr/bin/lsb_release -sc)
PROJECT_ROOT=/srv/mev-backend

# install dependencies
/usr/bin/curl -sO "https://apt.puppetlabs.com/puppet6-release-$CODENAME.deb"
/usr/bin/dpkg -i "puppet6-release-$CODENAME.deb"
/usr/bin/apt-get -qq update
/usr/bin/apt-get -qq -y install puppet-agent

/usr/bin/git clone https://github.com/web-mev/mev-backend.git $PROJECT_ROOT
cd $PROJECT_ROOT && /usr/bin/git checkout ${var.git_branch}
