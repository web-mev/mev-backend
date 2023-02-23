resource "aws_sns_topic" "api_server_down" {
  name = "${local.common_tags.Name}-api-server-down-topic"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.api_server_down.arn
  protocol  = "email"
  endpoint  = var.django_superuser_email
}
