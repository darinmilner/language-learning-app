
# S3 bucket for certificate storage
resource "aws_s3_bucket" "certificate_bucket" {
  bucket = var.certificate_bucket
  acl    = "private"

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }

  lifecycle {
    prevent_destroy = true
  }

  tags = {
    Name = "Certificate Storage"
  }
}
