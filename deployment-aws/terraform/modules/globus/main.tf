# TODO: replace gcs to globus, move aws_s3_bucket.globus to module?

data "aws_s3_object" "deployment_key" {
  bucket = var.secrets_bucket
  # TODO: add globus prefix
  key    = "${var.secrets_prefix}/deployment-key.json"
}

data "aws_s3_object" "node_config" {
  bucket = var.secrets_bucket
  # TODO: add globus prefix
  key    = "${var.secrets_prefix}/node_config.json"
}

resource "aws_iam_role" "gcs_server" {
  name               = "${var.name_prefix}-gcs-role"
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

resource "aws_iam_role_policy" "gcs_s3_access" {
  name   = "${var.name_prefix}-gcs-config-bucket-access"
  role   = aws_iam_role.gcs_server.id
  policy = jsonencode(
    {
      Version   = "2012-10-17",
      Statement = [
        {
          Effect   = "Allow",
          Action   = "s3:GetObject",
          # TODO: replace hardcoded values with data source references
          Resource = "arn:aws:s3:::webmev-tf/secrets/*"
        }
      ]
    }
  )
}

# For adding SSM to the instance:
resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.gcs_server.id
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "gcs_server" {
  name = "${var.name_prefix}-gcs-profile"
  role = aws_iam_role.gcs_server.name
}

resource "aws_security_group" "globus_connect_server" {
  name        = "${var.name_prefix}-globus"
  description = "Allow inbound HTTPS and Globus-specific ports"
  vpc_id      = var.vpc_id
  ingress {
    description      = "HTTPS"
    from_port        = 443
    to_port          = 443
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }
  ingress {
    description      = "HTTP"
    from_port        = 50000
    to_port          = 51000
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }
  # implicit with AWS but Terraform requires this to be explicit
  egress {
    description      = "Allow all egress"
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }
}

resource "aws_instance" "gcs" {
  instance_type          = "t2.micro"
  monitoring             = true
  ami                    = "ami-0ab0629dba5ae551d"
  vpc_security_group_ids = [aws_security_group.globus_connect_server.id]
  subnet_id              = var.subnet_id
  iam_instance_profile   = aws_iam_instance_profile.gcs_server.name
  tags                   = {
    Name = "${var.name_prefix}-gcs"
  }
  user_data_replace_on_change = true
  root_block_device {
    volume_size = 12
    volume_type = "gp3"
    encrypted   = true
  }
  # TODO: remove sudo and add absolute system paths for executables
  user_data = <<-EOF
    #!/usr/bin/bash -ex

    # Instructions for installing GCS from:
    # https://docs.globus.org/globus-connect-server/v5.4/#globus_connect_server_prerequisites
    update-locale LANG=C.UTF-8

    mkdir -p /opt/software && cd /opt/software
    curl -LOs https://downloads.globus.org/globus-connect-server/stable/installers/repo/deb/globus-repo_latest_all.deb
    sudo dpkg -i globus-repo_latest_all.deb
    sudo apt-key add /usr/share/globus-repo/RPM-GPG-KEY-Globus
    sudo apt update
    sudo apt install -y globus-connect-server54 unzip

    # Also install ntp/ntpstat
    apt-get install -y ntp ntpstat
    service ntp start

    # install aws cli to download the config files
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "/tmp/awscliv2.zip"
    unzip /tmp/awscliv2.zip -d /tmp
    /tmp/aws/install

    aws s3 cp s3://${data.aws_s3_object.deployment_key.bucket}/${data.aws_s3_object.deployment_key.key} /root/deployment-key.json
    aws s3 cp s3://${data.aws_s3_object.node_config.bucket}/${data.aws_s3_object.node_config.key} /root/node_config.json

    globus-connect-server node setup \
    --deployment-key /root/deployment-key.json \
    --client-id ${var.endpoint_client_uuid} \
    --import-node /root/node_config.json \
    --secret ${var.endpoint_client_secret}

    systemctl restart apache2
  EOF
}
