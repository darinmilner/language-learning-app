resource "aws_security_group" "alb_sg" {
  vpc_id = aws_vpc.main.id

  tags = {
    Environment = var.environment
    Name        = "ALB Security Group"
  }
}

resource "aws_vpc_security_group_ingress_rule" "alb_sg_ingress" {
  for_each          = var.allowed_ips
  security_group_id = aws_security_group.alb_sg.id

  cidr_ipv4   = each.value
  from_port   = local.http_port
  ip_protocol = "tcp"
  to_port     = local.http_port
}

# Main security group (minimal configuration)
resource "aws_security_group" "ecs_service" {
  name        = "api-ecs-sg"
  description = "Security group for Fare Calculator API ECS service"
  vpc_id      = aws_vpc.main.id
}

resource "aws_vpc_security_group_ingress_rule" "ecs_ingress_alb" {
  for_each = var.allowed_ips
  description              = "Allow traffic from ALB on port 80"
  from_port                = 80
  to_port                  = 80
  ip_protocol                 = "tcp"
  security_group_id        = aws_security_group.alb_sg.id 

  tags = {
    Name = "allow-all-from-alb"
  }
}

resource "aws_vpc_security_group_ingress_rule" "all_ingress_alb" {
  description       = "Allow Inbound traffic from ALB"
  ip_protocol          = "-1"
  security_group_id = aws_security_group.alb_sg.id
  referenced_security_group_id = aws_security_group.ecs_service.id 

  tags = {
    Name = "allow-all-to-app"
  }
}

resource "aws_vpc_security_group_egress_rule" "app_egress" {
  description = "ECS egress rule"
  ip_protocol = "-1"
  cidr_ipv4 = "0.0.0.0/0"
  security_group_id = aws_security_group.ecs_service.id 

  tags = {
    Name = "allow-all-egress"
  }
}
