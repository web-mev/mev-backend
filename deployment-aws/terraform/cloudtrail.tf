resource "aws_cloudtrail" "webmev-cloudtrail" {
  name                    = "${local.common_tags.Name}-cloudtrail"
  s3_bucket_name          = aws_s3_bucket.log_bucket.id
  s3_key_prefix           = "${local.stack}"
  include_global_service_events = false
  event_selector {
    read_write_type           = "All"
    include_management_events = false

    data_resource {
      type = "AWS::S3::Object"
      values = [
          "${aws_s3_bucket.api_storage_bucket.arn}/",
          "${aws_s3_bucket.cromwell_storage_bucket.arn}/",
      ]
    }
  }
}