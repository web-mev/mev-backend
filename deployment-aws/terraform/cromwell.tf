resource "aws_iam_role" "cromwell" {
  name               = "${local.common_tags.Name}-cromwell"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [
      {
        Action    = "sts:AssumeRole"
        Effect    = "Allow"
        Sid       = ""
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      },
    ]
  })
}

resource "aws_iam_instance_profile" "cromwell" {
  name = "${local.common_tags.Name}-cromwell"
  role = aws_iam_role.cromwell.name
}

resource "aws_instance" "cromwell" {
  # Ubuntu 20.04 LTS https://cloud-images.ubuntu.com/locator/ec2/
  ami                    = "ami-07f84a50d2dec2fa4"
  instance_type          = "t3.medium"
  monitoring             = true
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.cromwell.id]
  ebs_optimized          = true
  iam_instance_profile   = aws_iam_instance_profile.cromwell.name
  key_name               = var.ssh_key_pair_name
  volume_tags            = local.common_tags
  root_block_device {
    volume_type = "gp3"
  }
  user_data_replace_on_change = true
  user_data                   = <<-EOT
  #!/usr/bin/bash -ex

  # https://serverfault.com/a/670688
  export DEBIAN_FRONTEND=noninteractive

  # to help Puppet determine the correct node name
  /usr/bin/hostnamectl set-hostname ${local.cromwell_cname}

  # install Puppet
  CODENAME=$(/usr/bin/lsb_release -sc)
  /usr/bin/curl -sO "https://apt.puppetlabs.com/puppet7-release-$CODENAME.deb"
  /usr/bin/dpkg -i "puppet7-release-$CODENAME.deb"
  /usr/bin/apt-get -qq update
  /usr/bin/apt-get -qq -y install puppet-agent

  # configure WebMEV
  export PROJECT_ROOT=/srv/mev-backend
  /usr/bin/mkdir $PROJECT_ROOT
  /usr/bin/chown ubuntu:ubuntu $PROJECT_ROOT
  /usr/bin/su -c "git clone https://github.com/web-mev/mev-backend.git $PROJECT_ROOT" ubuntu
  /usr/bin/su -c "cd $PROJECT_ROOT && /usr/bin/git checkout -q ${local.commit_id}" ubuntu

  # install and configure librarian-puppet
  export PUPPET_ROOT="$PROJECT_ROOT/deployment-aws/puppet"
  /opt/puppetlabs/puppet/bin/gem install librarian-puppet -v 3.0.1 --no-document
  # need to set $HOME: https://github.com/rodjek/librarian-puppet/issues/258
  export HOME=/root
  /opt/puppetlabs/puppet/bin/librarian-puppet config path /opt/puppetlabs/puppet/modules --global
  /opt/puppetlabs/puppet/bin/librarian-puppet config tmp /tmp --global
  cd $PUPPET_ROOT
  PATH=$PATH:/opt/puppetlabs/bin
  /opt/puppetlabs/puppet/bin/librarian-puppet install

  # configure and run Puppet
  export FACTER_AWS_REGION='${data.aws_region.current.name}'
  export FACTER_API_STORAGE_BUCKET='${aws_s3_bucket.api_storage_bucket.id}'
  export FACTER_CROMWELL_STORAGE_BUCKET='${aws_s3_bucket.cromwell_storage_bucket.id}'
  export FACTER_CROMWELL_JOB_QUEUE='${aws_batch_job_queue.cromwell.arn}'

  /opt/puppetlabs/bin/puppet apply $PUPPET_ROOT/manifests/site.pp
  EOT
}

resource "aws_batch_compute_environment" "cromwell" {
  compute_environment_name = local.common_tags.Name
  type                     = "MANAGED"
  compute_resources {
    max_vcpus          = 16
    security_group_ids = [aws_security_group.cromwell.id]
    subnets            = [aws_subnet.public.id]
    type               = "FARGATE"
  }
  service_role = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/aws-service-role/batch.amazonaws.com/AWSServiceRoleForBatch"
}

resource "aws_batch_job_queue" "cromwell" {
  name                 = local.common_tags.Name
  compute_environments = [aws_batch_compute_environment.cromwell.arn]
  priority             = 1
  state                = "ENABLED"
}
