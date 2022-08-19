resource "aws_s3_bucket" "api_storage_bucket" {
    bucket = "${local.stack}-webmev-storage"
}