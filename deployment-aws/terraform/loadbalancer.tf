resource "aws_lb" "api" {
  # ALB is required for action type "redirect"
  name            = local.common_tags.Name
  ip_address_type = "dualstack"
  subnets         = [aws_subnet.public.id, aws_subnet.extra.id]
  security_groups = [aws_security_group.load_balancer.id]
  access_logs {
    bucket  = "webmev-logs"
    prefix  = "${local.stack}-lb"
    enabled = true
  }
}

resource "aws_lb_target_group" "api" {
  name     = local.common_tags.Name
  port     = 80
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id
}

resource "aws_lb_target_group_attachment" "api" {
  target_group_arn = aws_lb_target_group.api.arn
  target_id        = aws_instance.api.id
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.api.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-2016-08"
  certificate_arn   = "arn:aws:acm:us-east-2:${data.aws_caller_identity.current.account_id}:certificate/3a63ddda-f80d-4318-a9b5-aa184c8a9e23"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.api.arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type = "redirect"
    redirect {
      port        = 443
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}
