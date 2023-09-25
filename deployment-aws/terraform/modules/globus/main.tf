# TODO: replace string gcs with globus

resource "aws_s3_bucket" "data" {
  bucket = var.data_bucket
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
          Resource = "arn:aws:s3:::${var.secrets_bucket}/${var.secrets_prefix}/*"
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
  # Ubuntu 22.04 LTS x86-64 LTS https://cloud-images.ubuntu.com/locator/ec2/
  ami                    = "ami-00d5c4dd05b5467c4"
  instance_type          = "t2.micro"
  monitoring             = true
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
  user_data = <<-EOF
    #!/usr/bin/bash -ex

    # Instructions for installing GCS from:
    # https://docs.globus.org/globus-connect-server/v5.4/#globus_connect_server_prerequisites
    /usr/sbin/update-locale LANG=C.UTF-8

    /usr/bin/curl --output-dir /tmp -O -s https://downloads.globus.org/globus-connect-server/stable/installers/repo/deb/globus-repo_latest_all.deb
    /usr/bin/dpkg -i /tmp/globus-repo_latest_all.deb
    /usr/bin/apt-key add /usr/share/globus-repo/RPM-GPG-KEY-Globus
    /usr/bin/apt update
    /usr/bin/apt install -y globus-connect-server54=5.4.67-1+gcs5.jammy ntp ntpstat unzip
    /usr/bin/systemctl start ntp

    # install AWS CLI to download the config files
    /usr/bin/curl --output-dir /tmp -O -s https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip
    /usr/bin/unzip /tmp/awscli-exe-linux-x86_64.zip -d /tmp
    /tmp/aws/install

    /usr/local/bin/aws s3 cp s3://${var.secrets_bucket}/${var.secrets_prefix}/deployment-key.json /root/deployment-key.json
    /usr/local/bin/aws s3 cp s3://${var.secrets_bucket}/${var.secrets_prefix}/node_config.json /root/node_config.json

    /usr/sbin/globus-connect-server node setup \
    --deployment-key /root/deployment-key.json \
    --client-id ${var.endpoint_client_uuid} \
    --import-node /root/node_config.json \
    --secret ${var.endpoint_client_secret}

    /usr/bin/systemctl restart apache2
  EOF
}
