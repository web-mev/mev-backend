resource "aws_cloudwatch_log_group" "default" {

  name = local.common_tags.Name

}