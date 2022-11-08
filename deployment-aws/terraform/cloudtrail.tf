resource "aws_cloudtrail" "webmev-cloudtrail" {
  name                    = "${local.common_tags.Name}-cloudtrail"
  s3_bucket_name          = data.aws_s3_bucket.s3_logging_bucket.id
}