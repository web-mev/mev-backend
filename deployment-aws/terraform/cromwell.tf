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

resource "aws_iam_role_policy" "cromwell_s3_access" {
  name   = "CromwellS3Access"
  role   = aws_iam_role.cromwell.id
  policy = jsonencode(
    {
      Version   = "2012-10-17",
      Statement = [
        {
          Effect   = "Allow",
          Resource = [
            "arn:aws:s3:::${aws_s3_bucket.cromwell_storage_bucket.id}",
            "arn:aws:s3:::${aws_s3_bucket.cromwell_storage_bucket.id}/*"
          ],
          Action = "s3:*"
        },
        {
          Effect   = "Allow",
          Resource = "*",
          Action   = [
            "s3:ListBucket",
            "s3:ListAllMyBuckets",
          ]
        }
      ]
    }
  )
}

resource "aws_iam_role_policy" "cromwell_batch_access" {
  name   = "CromwellBatchAccess"
  role   = aws_iam_role.cromwell.id
  policy = jsonencode(
    {
      Version   = "2012-10-17",
      Statement = [
        {
          Effect   = "Allow",
          Resource = "*",
          Action   = [
            "batch:DescribeJobQueues",
            "batch:DeregisterJobDefinition",
            "batch:TerminateJob",
            "batch:DescribeJobs",
            "batch:CancelJob",
            "batch:SubmitJob",
            "batch:RegisterJobDefinition",
            "batch:DescribeJobDefinitions",
            "batch:ListJobs",
            "batch:DescribeComputeEnvironments",
            "ecs:DescribeContainerInstances",
            "imagebuilder:GetComponent",
            "imagebuilder:GetContainerRecipe",
            "ecr:GetAuthorizationToken",
            "ecr:BatchGetImage",
            "ecr:InitiateLayerUpload",
            "ecr:UploadLayerPart",
            "ecr:CompleteLayerUpload",
            "ecr:BatchCheckLayerAvailability",
            "ecr:GetDownloadUrlForLayer",
            "ecr:PutImage",
            "ecr:CreateRepository"
          ]
        },
      ]
    }
  )
}

resource "aws_iam_role_policy" "cromwell_cloudwatch" {
  name   = "CromwellCloudWatchAccess"
  role   = aws_iam_role.cromwell.id
  policy = jsonencode({
    Version   = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Resource = "arn:aws:logs:*:*:*",
        Action   = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ]
      }
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
  tags                   = {
    Name = "${local.common_tags.Name}-cromwell"
  }
  volume_tags = merge(local.common_tags, { Name = "${local.common_tags.Name}-cromwell" })
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

resource "aws_iam_role" "ecs_instance" {
  name               = "${local.common_tags.Name}-ecs"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17",
    Statement = [
      {
        Action    = "sts:AssumeRole",
        Effect    = "Allow",
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_instance" {
  role       = aws_iam_role.ecs_instance.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role"
}

resource "aws_iam_instance_profile" "ecs_instance" {
  name = "${local.common_tags.Name}-ecs"
  role = aws_iam_role.ecs_instance.name
}

resource "aws_iam_role" "batch_service" {
  name               = "${local.common_tags.Name}-batch"
  assume_role_policy = jsonencode(
    {
      Version   = "2012-10-17",
      Statement = [
        {
          Action    = "sts:AssumeRole",
          Effect    = "Allow",
          Principal = {
            Service = "batch.amazonaws.com"
          }
        }
      ]
    }
  )
}

resource "aws_iam_role_policy_attachment" "batch_service" {
  role       = aws_iam_role.batch_service.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBatchServiceRole"
}

resource "aws_security_group" "batch_service" {
  name   = "${local.common_tags.Name}-batch"
  vpc_id = aws_vpc.main.id
  # implicit with AWS but Terraform requires this to be explicit
  egress {
    description      = "Allow all egress"
    from_port        = 0
    to_port          = 0
    protocol         = "all"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }
}

resource "aws_batch_compute_environment" "cromwell" {
  # need to use name prefix and lifecycle meta-argument to avoid a bug
  # https://github.com/hashicorp/terraform-provider-aws/issues/13221
  # https://discuss.hashicorp.com/t/error-error-deleting-batch-compute-environment-cannot-delete-found-existing-jobqueue-relationship/5408/4
  compute_environment_name_prefix = "${local.common_tags.Name}-"
  lifecycle {
    create_before_destroy = true
  }
  type         = "MANAGED"
  service_role = aws_iam_role.batch_service.arn
  depends_on   = [aws_iam_role_policy_attachment.batch_service]
  compute_resources {
    instance_role      = aws_iam_instance_profile.ecs_instance.arn
    instance_type      = ["c6i.large"]
    max_vcpus          = 16
    min_vcpus          = 0
    security_group_ids = [aws_security_group.batch_service.id]
    subnets            = [aws_subnet.public.id]
    type               = "EC2"
  }
}

resource "aws_batch_job_queue" "cromwell" {
  name                 = local.common_tags.Name
  compute_environments = [aws_batch_compute_environment.cromwell.arn]
  priority             = 1
  state                = "ENABLED"
}
