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
