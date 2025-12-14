resource "aws_lb" "app_alb" {
  name               = "app-alb"
  internal           = false
  load_balancer_type = "application"
  subnets            = [for subnet in aws_subnet.public_subnet : subnet.id]

  # TODO: Add Access Logs
  tags = {
    Environment = var.environment
  }
}

resource "aws_lb_listener" "alb_listener" {
  load_balancer_arn = aws_lb.app_alb.arn
  port              = local.http_port
  protocol          = local.http_protocol

  default_action {
    type = "fixed-response"
    fixed_response {
      content_type = "text/plain"
      message_body = "ALB is working"
    }
  }
}
