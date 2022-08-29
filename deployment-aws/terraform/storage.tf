resource "aws_s3_bucket" "api_storage_bucket" {
    bucket = "${local.stack}-webmev-storage"
}

resource "aws_s3_bucket" "cromwell_storage_bucket" {
    bucket = "${local.stack}-cromwell-storage"
}
