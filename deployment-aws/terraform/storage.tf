resource "aws_s3_bucket" "api_storage_bucket" {
    bucket = "${local.stack}-webmev-storage"
}

resource "aws_s3_bucket" "cromwell_storage_bucket" {
    bucket = "${local.stack}-cromwell-storage"
}

resource "aws_s3_bucket_cors_configuration" "storage_bucket_cors" {
  bucket = aws_s3_bucket.api_storage_bucket.id

  cors_rule {
    allowed_headers = ["RANGE", "Cache-control", "If-None-Match", "Content-Type"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = ["https://${var.frontend_domain}"]
    expose_headers  = ["Content-Length", "Content-Range", "Content-Type"]
    max_age_seconds = 3000
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "main_storage_encryption_config" {
  bucket = aws_s3_bucket.api_storage_bucket.bucket

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.main_storage_kms_key.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "cromwell_storage_encryption_config" {
  bucket = aws_s3_bucket.cromwell_storage_bucket.bucket

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.cromwell_storage_kms_key.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}
