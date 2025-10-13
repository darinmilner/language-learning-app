provider "aws" {
  region = var.aws_region
}

# Dynamic Lambda function creation using for_each
resource "aws_lambda_function" "certificate_management" {
  for_each = local.lambda_functions

  filename      = each.value.filename
  function_name = each.key
  role          = aws_iam_role.lambda_role.arn
  handler       = each.value.handler
  runtime       = var.runtime
  timeout       = each.value.timeout
  layers        = each.value.layers

  dynamic "environment" {
    for_each = length(each.value.environment) > 0 ? [1] : []
    content {
      variables = merge(
        each.value.environment,
        {
          S3_BUCKET = aws_s3_bucket.certificate_bucket.bucket
        }
      )
    }
  }

  kms_key_arn = aws_kms_key.certificate_management.arn

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic_execution,
    aws_cloudwatch_log_group.lambda_logs
  ]
}

# CloudWatch Log Groups for each Lambda
resource "aws_cloudwatch_log_group" "lambda_logs" {
  for_each = local.lambda_functions

  name              = "/aws/lambda/${each.key}"
  retention_in_days = 30

  tags = {
    Environment = "production"
  }
}

# Lambda Alias for each function
resource "aws_lambda_alias" "certificate_management" {
  for_each = local.lambda_functions

  name             = "production"
  function_name    = aws_lambda_function.certificate_management[each.key].function_name
  function_version = "$LATEST"

  depends_on = [aws_lambda_function.certificate_management]
}