# EventBridge Rule for monthly certificate check
resource "aws_cloudwatch_event_rule" "monthly_cert_check" {
  name                = "monthly-certificate-check"
  description         = "Trigger certificate check on the first day of every month"
  schedule_expression = "cron(0 2 1 * ? *)" # 2 AM on the 1st day of every month

  tags = {
    Environment = "production"
    Purpose     = "certificate-management"
  }
}

# EventBridge Target for Step Function
resource "aws_cloudwatch_event_target" "step_function_target" {
  rule      = aws_cloudwatch_event_rule.monthly_cert_check.name
  target_id = "certificate-manager-step-function"
  arn       = aws_sfn_state_machine.certificate_manager.arn
  role_arn  = aws_iam_role.eventbridge_role.arn

  input = jsonencode({
    domain = var.domain
  })
}

# IAM Role for EventBridge to trigger Step Function
resource "aws_iam_role" "eventbridge_role" {
  name = "eventbridge-certificate-management-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Environment = "production"
  }
}

# IAM Policy for EventBridge to execute Step Function
resource "aws_iam_role_policy" "eventbridge_step_function_policy" {
  name = "eventbridge-step-function-policy"
  role = aws_iam_role.eventbridge_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "states:StartExecution"
        Resource = aws_sfn_state_machine.certificate_manager.arn
      }
    ]
  })
}