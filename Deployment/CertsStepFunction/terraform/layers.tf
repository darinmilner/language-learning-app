# Lambda layer for shared Python dependencies
resource "aws_lambda_layer_version" "shared_python_layer" {
  filename            = "layers/python_layer.zip"
  layer_name          = "python-layer"
  description         = "Shared Python dependencies for certificate management"
  compatible_runtimes = ["python3.12"]
  source_code_hash    = filebase64sha256("layers/python-layer.zip")
}