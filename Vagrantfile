# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/focal64"

  config.vm.hostname = "mev-cromwell"

  config.vm.provider "virtualbox" do |vb|
    vb.memory = 1024
    vb.cpus = 2
  end

  config.vm.provision "shell", inline: <<-SHELL
    # https://serverfault.com/a/670688
    export DEBIAN_FRONTEND=noninteractive
    # exit immediately on errors in any command
    set -e
    # print commands and their expanded arguments
    set -x

    # install Puppet
    CODENAME=$(/usr/bin/lsb_release -sc)
    /usr/bin/curl -sO "https://apt.puppetlabs.com/puppet6-release-$CODENAME.deb"
    /usr/bin/dpkg -i "puppet6-release-$CODENAME.deb"
    /usr/bin/apt-get -qq update
    /usr/bin/apt-get -qq -y install puppet-agent

    # install and configure librarian-puppet
    /opt/puppetlabs/puppet/bin/gem install librarian-puppet -v 3.0.1 --no-document
    /opt/puppetlabs/puppet/bin/librarian-puppet config path /opt/puppetlabs/puppet/modules --global
    /opt/puppetlabs/puppet/bin/librarian-puppet config tmp /tmp --global
    PATH="${PATH}:/opt/puppetlabs/bin" && cd /vagrant/deploy/puppet && /opt/puppetlabs/puppet/bin/librarian-puppet install

    /opt/puppetlabs/bin/puppet apply /vagrant/deploy/puppet/manifests/site.pp
  SHELL
end