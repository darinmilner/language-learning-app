resource "aws_ecs_cluster" "ecs_cluster" {
  name = "app-ecs-cluster"
}

# --- ECS Execution Role ---
resource "aws_iam_role" "ecs_execution_role" {
  name = "task-ecs-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })

  tags =  {
    Role = "ECS Execution"
  }
}

resource "aws_iam_role_policy_attachment" "ecs_execution_policy" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}