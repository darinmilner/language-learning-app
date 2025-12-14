resource "aws_ecs_task_definition" "service" {
  family = "${var.app_name}-task"
  requires_compatibilities = [ "FARGATE" ]
  network_mode = "awsvpc"
  cpu = "256"
  memory = "512"
  execution_role_arn = var.execution_role_arn
  container_definitions = jsonencode({
    name = var.app_name
    image = "${local.ecr_url}"
    cpu = 256
    memory = 512
    essential = true 
    portMappings = [
        {
            containerPort = var.port 
            hostPort = var.port 
        }
    ]
  })
}

resource "aws_ecs_service" "fare_calculator_api" {
  name            = "${var.app_name}-service"
  cluster         = var.ecs_cluster_id
  task_definition = aws_ecs_task_definition.service.arn 
  launch_type     = "FARGATE"
  desired_count = 1

  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = [var.ecs_security_group_id]
    assign_public_ip = var.is_public
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.fare_calculator_api.arn
    container_name   = "ui-api"
    container_port   = 8000
  }

  deployment_controller {
    type = "ECS"
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  enable_ecs_managed_tags = true
  propagate_tags          = "SERVICE"
}