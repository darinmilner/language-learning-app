provider "aws" {
  region = var.aws_region
}

# Lambda functions
resource "aws_lambda_function" "check_certificate" {
  filename      = "lambdas/check_certificate.zip"
  function_name = "check_certificate"
  role          = aws_iam_role.lambda_role.arn
  handler       = "index.lambda_handler"
  runtime       = "python3.12"
  layers        = [aws_lambda_layer_version.shared_python_layer.arn]

  environment {
    variables = {
      CERTIFICATE_BUCKET = var.certificate_bucket
    }
  }
}

resource "aws_lambda_function" "generate_certificate" {
  filename      = "lambdas/generate_certificate.zip"
  function_name = "generate_certificate"
  role          = aws_iam_role.lambda_role.arn
  handler       = "index.lambda_handler"
  runtime       = "python3.12"
  timeout       = 300 # 5 minutes for Certbot operations
  layers        = [aws_lambda_layer_version.shared_python_layer.arn]

  environment {
    variables = {
      CERTIFICATE_BUCKET = var.certificate_bucket
    }
  }
}

resource "aws_lambda_function" "replace_certificate" {
  filename      = "lambdas/replace_certificate.zip"
  function_name = "replace_certificate"
  role          = aws_iam_role.lambda_role.arn
  handler       = "index.lambda_handler"
  runtime       = "python3.12"
  layers        = [aws_lambda_layer_version.shared_python_layer.arn]

  environment {
    variables = {
      CERTIFICATE_BUCKET = var.certificate_bucket
    }
  }
}
