resource "aws_cloudwatch_log_group" "default" {
  name = local.common_tags.Name
}

resource "aws_cloudwatch_metric_alarm" "instance_healthcheck" {
  # Checks the instance- things like memory, fileystem corruption, etc.
  # See: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/monitoring-system-instance-status-check.html
  # Some further explanation:
  # If the instance check fails, the metric will produce the value of 1.
  # If we calculate the average over a 5-minute period and that value is
  # greater than 0.8, then there's something wrong. 
  alarm_name          = "${local.common_tags.Name}-healthcheck-instance-alarm"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  # https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/viewing_metrics_with_cloudwatch.html#status-check-metrics
  # metric can be 0 (passed) or 1 (failed)
  metric_name       = "StatusCheckFailed_Instance"
  namespace         = "AWS/EC2"
  period            = "300"
  statistic         = "Average"
  threshold         = 0.8
  alarm_description = "Instance status check for EC2."
  actions_enabled   = "true"
  alarm_actions     = [aws_sns_topic.api_server_down.arn]
  dimensions = {
    InstanceId = aws_instance.api.id
  }
}

resource "aws_cloudwatch_metric_alarm" "system_healthcheck" {
  # This is for 'system' checks- largely things related to the physical host, like network issues, etc.
  # See- https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/monitoring-system-instance-status-check.html
  # Some further explanation:
  # If the instance check fails, the metric will produce the value of 1.
  # If we calculate the average over a 5-minute period and that value is
  # greater than 0.8, then there's something wrong. 
  alarm_name          = "${local.common_tags.Name}-healthcheck-system-alarm"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  # https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/viewing_metrics_with_cloudwatch.html#status-check-metrics
  # metric can be 0 (passed) or 1 (failed)
  metric_name       = "StatusCheckFailed_System"
  namespace         = "AWS/EC2"
  period            = "300"
  statistic         = "Average"
  threshold         = 0.8
  alarm_description = "System status check for EC2."
  actions_enabled   = "true"
  alarm_actions     = [aws_sns_topic.api_server_down.arn]
  dimensions = {
    InstanceId = aws_instance.api.id
  }
}
