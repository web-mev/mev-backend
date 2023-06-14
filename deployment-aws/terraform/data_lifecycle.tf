resource "aws_iam_role" "data_lifecycle" {
  name = "${local.common_tags.Name}-dlm"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Service = "dlm.amazonaws.com"
        }
      },
    ]
  })
}


resource "aws_iam_role_policy" "data_lifecycle" {
  name = "${local.common_tags.Name}-dlm-policy"
  role = aws_iam_role.data_lifecycle.id
  policy = jsonencode(
    {
      Version = "2012-10-17",
      Statement = [
        {
          Effect = "Allow",
          Action = [
            "ec2:CreateSnapshot",
            "ec2:CreateSnapshots",
            "ec2:DeleteSnapshot",
            "ec2:DescribeInstances",
            "ec2:DescribeVolumes",
            "ec2:DescribeSnapshots"
          ],
          # TODO: can/should we limit this to the specific EBS volume and api instance?
          Resource = ["*"]
        },
        {
          Effect = "Allow",
          Action = "ec2:CreateTags",
          Resource = [
            "arn:aws:ec2:*::snapshot/*"
          ]
        }
      ]
    }
  )
}


resource "aws_dlm_lifecycle_policy" "dlm" {
  description        = "Daily backup of EBS volume"
  execution_role_arn = aws_iam_role.data_lifecycle.arn
  state              = "ENABLED"
  tags = {
    Name = "${local.common_tags.Name}-dlm"
  }

  policy_details {
    resource_types     = ["VOLUME"]
    resource_locations = ["CLOUD"]
    policy_type        = "EBS_SNAPSHOT_MANAGEMENT"

    # this dictates what we are actually looking to snapshot:
    target_tags = {
      Name = "${local.common_tags.Name}-ebs"
    }

    schedule {
      name      = "Daily backup of EBS volume for data"
      copy_tags = true

      create_rule {
        interval      = 24
        interval_unit = "HOURS"
        times         = ["23:30"]
      }

      retain_rule {
        interval      = "7"
        interval_unit = "DAYS"
      }

      tags_to_add = {
        data_backup      = true
        snapshot_creator = "dlm"
      }
    }
  }
}