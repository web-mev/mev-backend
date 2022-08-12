resource "random_id" "database_snapshot" {
  byte_length = 4
}

resource "random_password" "database_superuser" {
  length  = 8
  special = false
}

resource "random_password" "database_user" {
  length  = 8
  special = false
}

resource "aws_db_instance" "default" {
  identifier                 = local.common_tags.Name
  instance_class             = "db.t3.micro"
  engine                     = "postgres"
  engine_version             = "12"
  auto_minor_version_upgrade = true
  allocated_storage          = 5
  storage_type               = "standard"
  username                   = "postgres"
  password                   = random_password.database_superuser.result
  final_snapshot_identifier  = "${local.common_tags.Name}-final-${random_id.database_snapshot.hex}"
  db_subnet_group_name       = aws_db_subnet_group.default.name
  vpc_security_group_ids     = [aws_security_group.database.id]
}
