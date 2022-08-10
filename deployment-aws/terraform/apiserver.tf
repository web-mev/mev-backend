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
  user_data_replace_on_change = true
  root_block_device {
    volume_type = "gp3"
  }
}
