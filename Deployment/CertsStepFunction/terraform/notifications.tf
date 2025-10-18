# SNS Topic for notifications
resource "aws_sns_topic" "certificate_notifications" {
  count = var.enable_sns_notifications ? 1 : 0

  name = "certificate-notifications-${var.env}"

  tags = merge(local.common_tags, {
    Purpose = "certificate-notifications"
  })
}

# SNS Topic Policy
resource "aws_sns_topic_policy" "certificate_notifications" {
  count = var.enable_sns_notifications ? 1 : 0

  arn = aws_sns_topic.certificate_notifications[0].arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = "*"
        }
        Action = [
          "SNS:Publish",
          "SNS:GetTopicAttributes"
        ]
        Resource = aws_sns_topic.certificate_notifications[0].arn
        Condition = {
          ArnEquals = {
            "aws:SourceArn" = [
              aws_sfn_state_machine.certificate_manager.arn,
              aws_lambda_function.certificate_management["check_certificate"].arn,
              aws_lambda_function.certificate_management["generate_certificate"].arn,
              aws_lambda_function.certificate_management["replace_certificate"].arn,
              aws_lambda_function.notification.arn
            ]
          }
        }
      }
    ]
  })
}

# SNS Email Subscription
resource "aws_sns_topic_subscription" "email_notifications" {
  count = var.enable_sns_notifications && length(var.notification_emails) > 0 ? length(var.notification_emails) : 0

  topic_arn = aws_sns_topic.certificate_notifications[0].arn
  protocol  = "email"
  endpoint  = var.notification_emails[count.index]
}

# Notification Lambda Function
resource "aws_lambda_function" "notification" {
  filename      = "lambdas/notification.zip"
  function_name = "certificate-notification"
  role          = aws_iam_role.lambda_role.arn
  handler       = "index.lambda_handler"
  runtime       = var.runtime
  timeout       = var.timeout

  environment {
    variables = {
      SNS_TOPIC_ARN = var.enable_sns_notifications ? aws_sns_topic.certificate_notifications[0].arn : ""
      S3_BUCKET     = data.aws_s3_bucket.certificate_bucket.bucket
      LOG_LEVEL     = var.log_level
    }
  }

  kms_key_arn = aws_kms_key.certificate_management.arn

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic_execution
  ]

  tags = local.common_tags
}

# SNS Trigger for Notification Lambda
resource "aws_lambda_permission" "sns_lambda_trigger" {
  count = var.enable_sns_notifications ? 1 : 0

  statement_id  = "AllowExecutionFromSNS"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.notification.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.certificate_notifications[0].arn
}

# SNS Subscription for Lambda
resource "aws_sns_topic_subscription" "lambda_notifications" {
  count = var.enable_sns_notifications ? 1 : 0

  topic_arn = aws_sns_topic.certificate_notifications[0].arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.notification.arn
}

# CloudWatch Log Group for Notification Lambda
resource "aws_cloudwatch_log_group" "notification_logs" {
  name              = "/aws/lambda/certificate-notification"
  retention_in_days = 30

  tags = local.common_tags
}