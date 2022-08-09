resource "aws_instance" "api" {
  # Ubuntu 20.04 LTS https://cloud-images.ubuntu.com/locator/ec2/
  ami                    = "ami-07f84a50d2dec2fa4"
  instance_type          = "t3.large"
  monitoring             = true
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.api_server.id]
  ebs_optimized          = true
  key_name               = var.ssh_key_pair_name
  volume_tags = local.common_tags
  root_block_device {
    volume_type = "gp3"
  }
  user_data_replace_on_change = true
  user_data = <<-EOT
  #!/usr/bin/bash -ex

  # https://serverfault.com/a/670688
  export DEBIAN_FRONTEND=noninteractive

  # derived from workspace name: dev, production, etc
  FACTER_ENVIRONMENT='${local.stack}'

  # Specify the appropriate settings file.
  # We do this here so it's prior to cycling the supervisor daemon
  if [ $FACTER_ENVIRONMENT = 'dev' ]; then
    FACTER_DJANGO_SETTINGS_MODULE=mev.settings_dev
  else
    FACTER_DJANGO_SETTINGS_MODULE=mev.settings_production
  fi
  # temp workaround required for Celery
  DJANGO_SETTINGS_MODULE=$FACTER_DJANGO_SETTINGS_MODULE

  # The commit identifier which we will deploy
  GIT_COMMIT='${var.git_commit}'

  # The frontend can be located on a different server.
  # This is used for communications, etc. (such as verification emails)
  # which will direct the user to a link on the front-end
  FACTER_FRONTEND_DOMAIN='${var.frontend_domain}'

  # The domain of the API:
  FACTER_BACKEND_DOMAIN='${var.backend_domain}'

  EOT
}
