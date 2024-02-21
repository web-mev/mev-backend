# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/jammy64"

  config.vm.provision "shell", inline: <<-SHELL
    # https://serverfault.com/a/670688
    export DEBIAN_FRONTEND=noninteractive
    # exit immediately on errors in any command
    set -e
    # print commands and their expanded arguments
    set -x

    # install Puppet
    OS_CODENAME=$(/usr/bin/lsb_release -sc)
    PUPPET_PACKAGE=puppet8-release-${OS_CODENAME}.deb
    /usr/bin/curl -sO "https://apt.puppetlabs.com/${PUPPET_PACKAGE}"
    /usr/bin/dpkg -i "$PUPPET_PACKAGE"
    /usr/bin/apt-get -qq update
    /usr/bin/apt-get -qq -y install puppet-agent

    # install and configure librarian-puppet
    /opt/puppetlabs/puppet/bin/gem install librarian-puppet -v 5.0.0 --no-document
    /opt/puppetlabs/puppet/bin/librarian-puppet config path /opt/puppetlabs/puppet/modules --global
    /opt/puppetlabs/puppet/bin/librarian-puppet config tmp /tmp --global
    PATH="${PATH}:/opt/puppetlabs/bin" && cd /vagrant/deployment-aws/puppet && /opt/puppetlabs/puppet/bin/librarian-puppet install
  SHELL

  config.vm.provision :puppet do |puppet|
    # Users can specify optional args in the local environment
    # These ENV vars must be sourced prior to `vagrant up`
    if ENV['DJANGO_SETTINGS_MODULE']
      puppet.facter['django_settings_module'] = ENV['DJANGO_SETTINGS_MODULE']
    end
    if ENV['FROM_EMAIL']
      puppet.facter['from_email'] = ENV['FROM_EMAIL']
    end
    if ENV['EMAIL_HOST']
      puppet.facter['email_host'] = ENV['EMAIL_HOST']
    end
    if ENV['EMAIL_HOST_USER']
      puppet.facter['email_host_user'] = ENV['EMAIL_HOST_USER']
    end
    if ENV['EMAIL_HOST_PASSWORD']
      puppet.facter['email_host_password'] = ENV['EMAIL_HOST_PASSWORD']
    end
    if ENV['ADMIN_EMAIL_CSV']
      puppet.facter['admin_email_csv'] = ENV['ADMIN_EMAIL_CSV']
    end
    if ENV['CONTAINER_REGISTRY']
      puppet.facter['container_registry'] = ENV['CONTAINER_REGISTRY']
    end
    if ENV['DOCKER_REPO_ORG']
      puppet.facter['docker_repo_org'] = ENV['DOCKER_REPO_ORG']
    end

    puppet.manifests_path = "deployment-aws/puppet/manifests"
    puppet.manifest_file  = "site.pp"
  end

  config.vm.define "api", primary: true do |api|
    api.vm.hostname = "mev-api"

    api.vm.network "forwarded_port", guest: 80, host: 8080  # Gunicorn
    api.vm.network "forwarded_port", guest: 8000, host: 8000  # Django dev server
    api.vm.network "forwarded_port", guest: 8983, host: 8983  # Solr

    api.vm.provider "virtualbox" do |vb|
      vb.memory = 4096
      vb.cpus = 2
    end
  end
end
