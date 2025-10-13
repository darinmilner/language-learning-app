# Step Function with external JSON definition
resource "aws_sfn_state_machine" "certificate_manager" {
  name     = "certificate_manager"
  role_arn = aws_iam_role.step_function_role.arn

  definition = templatefile("${path.module}/lambdas/function.json", {
    check_certificate_lambda_arn    = aws_lambda_function.certificate_management["check_certificate"].arn
    generate_certificate_lambda_arn = aws_lambda_function.certificate_management["generate_certificate"].arn
    replace_certificate_lambda_arn  = aws_lambda_function.certificate_management["replace_certificate"].arn
    certificate_bucket_name         = aws_s3_bucket.certificate_bucket.bucket
  })

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.step_function_logs.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  tags = {
    Environment = "production"
  }
}

# CloudWatch Log Group for Step Function
resource "aws_cloudwatch_log_group" "step_function_logs" {
  name              = "/aws/vendedlogs/states/certificate_manager"
  retention_in_days = 30

  tags = {
    Environment = "production"
  }
}