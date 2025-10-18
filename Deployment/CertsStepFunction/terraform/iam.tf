# IAM roles and policies
resource "aws_iam_role" "lambda_role" {
  name = "lambda_certificate_manager_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role" "step_function_role" {
  name = "step_function_certificate_manager_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
      }
    ]
  })
}

# Step Function role for invoking notification Lambda
resource "aws_iam_role_policy" "step_function_notification_lambda" {
  name = "step_function_notification_lambda"
  role = aws_iam_role.step_function_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = [
          aws_lambda_function.notification.arn
        ]
      }
    ]
  })
}

# SNS permissions for Lambda functions
resource "aws_iam_role_policy" "lambda_sns_policy" {
  count = var.enable_sns_notifications ? 1 : 0

  name = "lambda_sns_policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sns:Publish",
          "sns:GetTopicAttributes"
        ]
        Resource = [
          aws_sns_topic.certificate_notifications[0].arn
        ]
      }
    ]
  })
}

# Lambda permissions for SNS to invoke
resource "aws_iam_role_policy" "sns_lambda_invoke_policy" {
  count = var.enable_sns_notifications ? 1 : 0

  name = "sns_lambda_invoke_policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = [
          aws_lambda_function.notification.arn
        ]
      }
    ]
  })
}