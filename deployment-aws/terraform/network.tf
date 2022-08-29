resource "aws_vpc" "main" {
  cidr_block                       = "172.16.0.0/16"
  assign_generated_ipv6_cidr_block = true
  enable_dns_hostnames             = true
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
  route {
    ipv6_cidr_block = "::/0"
    gateway_id      = aws_internet_gateway.main.id
  }
}

resource "aws_subnet" "public" {
  vpc_id                          = aws_vpc.main.id
  availability_zone               = "${data.aws_region.current.name}a"
  cidr_block                      = cidrsubnet(aws_vpc.main.cidr_block, 8, 0)
  ipv6_cidr_block                 = cidrsubnet(aws_vpc.main.ipv6_cidr_block, 8, 0)
  map_public_ip_on_launch         = true
  assign_ipv6_address_on_creation = true
}

resource "aws_subnet" "extra" {
  # currently unused but ALB requires at least two subnets in two different AZs
  vpc_id            = aws_vpc.main.id
  availability_zone = "${data.aws_region.current.name}b"
  cidr_block        = cidrsubnet(aws_vpc.main.cidr_block, 8, 1)
  ipv6_cidr_block   = cidrsubnet(aws_vpc.main.ipv6_cidr_block, 8, 1)
}

resource "aws_route_table_association" "public" {
  route_table_id = aws_route_table.public.id
  subnet_id      = aws_subnet.public.id
}

resource "aws_subnet" "private_a" {
  vpc_id                          = aws_vpc.main.id
  availability_zone               = "${data.aws_region.current.name}a"
  cidr_block                      = cidrsubnet(aws_vpc.main.cidr_block, 8, 10)
  ipv6_cidr_block                 = cidrsubnet(aws_vpc.main.ipv6_cidr_block, 8, 10)
  assign_ipv6_address_on_creation = true
}
# currently unused but required for RDS aws_db_subnet_group
resource "aws_subnet" "private_b" {
  vpc_id                          = aws_vpc.main.id
  availability_zone               = "${data.aws_region.current.name}b"
  cidr_block                      = cidrsubnet(aws_vpc.main.cidr_block, 8, 11)
  ipv6_cidr_block                 = cidrsubnet(aws_vpc.main.ipv6_cidr_block, 8, 11)
  assign_ipv6_address_on_creation = true
}
resource "aws_db_subnet_group" "default" {
  name       = local.common_tags.Name
  subnet_ids = [aws_subnet.private_a.id, aws_subnet.private_b.id]
}

resource "aws_security_group" "database" {
  name        = "${local.common_tags.Name}-database"
  description = "Allow incoming connections to PostgreSQL instance from the API server"
  vpc_id      = aws_vpc.main.id
  ingress {
    description     = "PostrgeSQL"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.api_server.id]
  }
}

resource "aws_security_group" "load_balancer" {
  name        = "${local.common_tags.Name}-loadbalancer"
  description = "Allow HTTP and HTTPS access"
  vpc_id      = aws_vpc.main.id
}
# using standalone security group rules for ALB to avoid cycle errors
resource "aws_security_group_rule" "http_ingress" {
  description       = "Allow inbound HTTP from Internet to ALB"
  type              = "ingress"
  from_port         = 80
  to_port           = 80
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  ipv6_cidr_blocks  = ["::/0"]
  security_group_id = aws_security_group.load_balancer.id
}
resource "aws_security_group_rule" "https_ingress" {
  description       = "Allow inbound HTTPS from Internet to ALB"
  type              = "ingress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  ipv6_cidr_blocks  = ["::/0"]
  security_group_id = aws_security_group.load_balancer.id
}
resource "aws_security_group_rule" "http_egress" {
  description              = "Allow HTTP from ALB to web server"
  type                     = "egress"
  from_port                = 80
  to_port                  = 80
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.api_server.id
  security_group_id        = aws_security_group.load_balancer.id
}

resource "aws_security_group" "api_server" {
  name        = "${local.common_tags.Name}-apiserver"
  description = "Allow inbound HTTP from ALB and SSH from the Internet"
  vpc_id      = aws_vpc.main.id
  ingress {
    description     = "HTTP from ALB"
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.load_balancer.id]
  }
  ingress {
    description      = "SSH from the Internet"
    from_port        = 22
    to_port          = 22
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }
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

resource "aws_security_group" "cromwell" {
  name        = "${local.common_tags.Name}-cromwell"
  description = "Allow inbound HTTP from API server and SSH from the Internet"
  vpc_id      = aws_vpc.main.id
  ingress {
    description     = "HTTP from API server"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.api_server.id]
  }
  ingress {
    description      = "SSH from the Internet"
    from_port        = 22
    to_port          = 22
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }
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
