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

resource "aws_s3_bucket_policy" "allow_cloudtrail_logging"  {
  bucket = data.aws_s3_bucket.s3_logging_bucket.id
  policy = data.aws_iam_policy_document.allow_cloud_trail_logging_policy.json
}

data "aws_s3_bucket" "s3_logging_bucket" {
  bucket = var.log_bucket_name
}


data "aws_iam_policy_document" "allow_cloud_trail_logging_policy" {
  
  statement {

    sid = "AWSCloudTrailAclCheck"

    principals {
      type = "Service"
      identifiers = ["cloudtrail.amazonaws.com"]
    }

    effect = "Allow"

    actions = [
      "s3:GetBucketAcl"
    ]

    resources = [
      "arn:aws:s3:::${var.log_bucket_name}"
    ]

    condition {
      test = "StringEquals"
      variable = "aws:SourceArn"
      values = ["arn:aws:cloudtrail:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:trail/${aws_cloudtrail.webmev-cloudtrail.id}"]
    }

  }

  statement {

    sid = "AWSCloudTrailWrite"

    principals {
      type = "Service"
      identifiers = ["cloudtrail.amazonaws.com"]
    }

    effect = "Allow"

    actions = [
      "s3:PutObject"
    ]

    resources = [
      "arn:aws:s3:::${var.log_bucket_name}/*/AWSLogs/${data.aws_caller_identity.current.account_id}/*"
    ]

    condition  {
      test = "StringEquals"
      variable = "aws:SourceArn"
      values = ["arn:aws:cloudtrail:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:trail/${aws_cloudtrail.webmev-cloudtrail.id}"]
    }

    condition  {
      test = "StringEquals"
      variable = "s3:x-amz-acl"
      values = ["bucket-owner-full-control"]
    }

  }
}