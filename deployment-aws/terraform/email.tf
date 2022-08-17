resource "aws_iam_user" "ses" {
  name = "${local.common_tags.Name}-ses"
}

resource "aws_iam_user_policy" "ses_send_email" {
  name   = "AllowSendingEmailThroughSES"
  user   = aws_iam_user.ses.name
  # https://docs.aws.amazon.com/ses/latest/dg/smtp-credentials.html#smtp-credentials-convert
  policy = <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "ses:SendRawEmail",
      "Effect": "Allow",
      "Resource": "*"
    }
  ]
}
POLICY
}

resource "aws_iam_access_key" "ses_user" {
  user = aws_iam_user.ses.name
}
