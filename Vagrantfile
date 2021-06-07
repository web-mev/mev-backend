# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/focal64"

  config.vm.hostname = "mev-cromwell"

  config.vm.provider "virtualbox" do |vb|
    vb.memory = 1024
    vb.cpus = 2
  end

  config.vm.provision :shell do |s| 
    s.path = "deploy/terraform/modules/api/mev_provision.sh"
    s.env = {
      environment=ENV["ENVIRONMENT"]
      db_name=ENV["DB_NAME"]
      db_user=ENV["DB_USER"]
      db_passwd=ENV["DB_PASSWD"]
      root_db_passwd=ENV["ROOT_DB_PASSWD"]
      db_port=ENV["DB_PORT"]
      db_host=ENV["DB_HOST_FULL"]
      frontend_domain="mydomain.com"
      domain=ENV["BACKEND_DOMAIN"]
      django_secret=ENV["DJANGO_SECRET_KEY"]

      # needed for production, but leave blank for local dev
      load_balancer_ip=""
      other_cors_origins=ENV["OTHER_CORS_ORIGINS"]
      django_superuser_passwd=ENV["DJANGO_SUPERUSER_PASSWORD"]
      django_superuser_email=ENV["DJANGO_SUPERUSER_EMAIL"]
      mev_storage_bucket=ENV[""]
      service_account_email=ENV[""]
      email_backend=ENV[""]
      from_email=ENV[""]
      gmail_access_token=ENV[""]
      gmail_refresh_token=ENV[""]
      gmail_client_id=ENV[""]
      gmail_client_secret=ENV[""]
      sentry_url=ENV[""]
      dockerhub_username=ENV[""]
      dockerhub_passwd=ENV[""]
      cromwell_bucket=ENV[""]
      cromwell_ip=ENV[""]
      branch=ENV[""]
    }
  end

end
