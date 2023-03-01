resource "aws_cloudwatch_log_group" "default" {
  name = local.common_tags.Name
}

resource "aws_cloudwatch_metric_alarm" "healthy_hosts" {
  # Some further explanation:
  # If the instance checks fail, the metric will produce the value of 1.
  # If we calculate the average over a 5-minute period and that value is
  # greater than 0.8, then there's something wrong. 
  alarm_name          = "${local.common_tags.Name}-healthcheck-alarm"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  # https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/viewing_metrics_with_cloudwatch.html#status-check-metrics
  # metric can be 0 (passed) or 1 (failed)
  metric_name       = "StatusCheckFailed"
  namespace         = "AWS/EC2"
  period            = "300"
  statistic         = "Average"
  threshold         = 0.8
  alarm_description = "Status check for EC2 instances"
  actions_enabled   = "true"
  alarm_actions     = [aws_sns_topic.api_server_down.arn]
  dimensions = {
    InstanceId = aws_instance.api.id
  }
}
