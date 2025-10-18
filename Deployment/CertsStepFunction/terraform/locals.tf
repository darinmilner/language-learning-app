locals {
  short_region = replace(var.aws_region, "-", "")
  common_tags = {
    Environment = var.env
  }
  lambda_functions = {
    check_certificate = {
      filename = "lambdas/check_certificate.zip"
      handler  = "index.lambda_handler"
      timeout  = var.timeout
      layers   = [aws_lambda_layer_version.shared_python_layer.arn]
      environment = {
        LOG_LEVEL = var.log_level
      }
    }
    generate_certificate = {
      filename = "lambdas/generate_certificate.zip"
      handler  = "index.lambda_handler"
      timeout  = var.timeout
      layers   = [aws_lambda_layer_version.shared_python_layer.arn]
      environment = {
        LOG_LEVEL     = var.log_level
        CERTBOT_EMAIL = var.certbot_email
      }
    }
    replace_certificate = {
      filename = "lambdas/replace_certificate.zip"
      handler  = "index.lambda_handler"
      timeout  = var.timeout
      layers   = [aws_lambda_layer_version.shared_python_layer.arn]
      environment = {
        LOG_LEVEL = var.log_level
      }
    }
  }
}