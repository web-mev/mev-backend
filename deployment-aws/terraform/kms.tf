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