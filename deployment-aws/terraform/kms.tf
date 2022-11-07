resource "aws_kms_key" "main_storage_kms_key" {
  description             = "This key is used to encrypt objects in the main storage bucket"
  
  # default, but be explicit here:
  key_usage               = "ENCRYPT_DECRYPT"
  enable_key_rotation     = true
  deletion_window_in_days = 10

  tags = {
    Name = "${local.common_tags.Name}-main-bucket-kms"
  }
}

resource "aws_kms_key" "cromwell_storage_kms_key" {
  description             = "This key is used to encrypt objects in the Cromwell bucket"
  
  # default, but be explicit here:
  key_usage               = "ENCRYPT_DECRYPT"
  enable_key_rotation     = true
  deletion_window_in_days = 10
  
  tags = {
    Name = "${local.common_tags.Name}-cromwell-bucket-kms"
  }
}

resource "aws_kms_key" "apiroot_ebs_kms_key" {
  description             = "This key is used to encrypt objects in the root EBS volume of the API server."
  
  # default, but be explicit here:
  key_usage               = "ENCRYPT_DECRYPT"
  enable_key_rotation     = true
  deletion_window_in_days = 10
  
  tags = {
    Name = "${local.common_tags.Name}-apiroot-ebs-kms"
  }
}

resource "aws_kms_key" "cromwellroot_ebs_kms_key" {
  description             = "This key is used to encrypt objects in the root EBS volume of the Cromwell server."
  
  # default, but be explicit here:
  key_usage               = "ENCRYPT_DECRYPT"
  enable_key_rotation     = true
  deletion_window_in_days = 10
  
  tags = {
    Name = "${local.common_tags.Name}-cromwellroot-ebs-kms"
  }
}

resource "aws_kms_key" "ebs_kms_key" {
  description             = "This key is used to encrypt objects in the EBS volume holding the majority of local data."
  
  # default, but be explicit here:
  key_usage               = "ENCRYPT_DECRYPT"
  enable_key_rotation     = true
  deletion_window_in_days = 10
  
  tags = {
    Name = "${local.common_tags.Name}-ebs-data-kms"
  }
}