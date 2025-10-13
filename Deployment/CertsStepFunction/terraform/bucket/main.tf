# S3 bucket for certificate storage with KMS encryption
resource "aws_s3_bucket" "certificate_bucket" {
  bucket = var.certificate_bucket
  acl    = "private"

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        kms_master_key_id = aws_kms_key.certificate_management.arn
        sse_algorithm     = "aws:kms"
      }
    }
  }

  versioning {
    enabled = true
  }

  lifecycle_rule {
    id      = "certificate_cleanup"
    enabled = true

    transition {
      days          = 30
      storage_class = "GLACIER"
    }

    expiration {
      days = 365
    }

    noncurrent_version_expiration {
      days = 30
    }
  }

  lifecycle {
    prevent_destroy = false
  }

  tags = {
    Name        = "Certificate Storage"
    Environment = "production"
  }
}

# S3 bucket policy to enforce KMS encryption
resource "aws_s3_bucket_policy" "certificate_bucket_policy" {
  bucket = aws_s3_bucket.certificate_bucket.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DenyUnEncryptedObjectUploads"
        Effect = "Deny"
        Principal = {
          AWS = "*"
        }
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.certificate_bucket.arn}/*"
        Condition = {
          StringNotEquals = {
            "s3:x-amz-server-side-encryption" = "aws:kms"
          }
        }
      },
      {
        Sid    = "DenyIncorrectKMSKey"
        Effect = "Deny"
        Principal = {
          AWS = "*"
        }
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.certificate_bucket.arn}/*"
        Condition = {
          StringNotEquals = {
            "s3:x-amz-server-side-encryption-aws-kms-key-id" = aws_kms_key.certificate_management.arn
          }
        }
      }
    ]
  })
}

# Allow test reports to be uploaded to the certificate bucket
resource "aws_s3_bucket_policy" "test_reports_policy" {
  bucket = aws_s3_bucket.certificate_bucket.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowTestReportsUpload"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action = [
          "s3:PutObject",
          "s3:PutObjectAcl"
        ]
        Resource = "${aws_s3_bucket.certificate_bucket.arn}/test-reports/*"
      },
      {
        Sid    = "AllowTestReportsRead"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          "${aws_s3_bucket.certificate_bucket.arn}/test-reports/*",
          "${aws_s3_bucket.certificate_bucket.arn}"
        ]
      }
    ]
  })
}