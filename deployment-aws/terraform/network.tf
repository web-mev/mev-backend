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
