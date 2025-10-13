# KMS Key for encrypting Lambda environment variables and S3 objects
resource "aws_kms_key" "certificate_management" {
  description             = "KMS key for certificate management Lambda functions and S3 encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow Lambda Functions to Use Key"
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.lambda_role.arn
        }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = "*"
      },
      {
        Sid    = "Allow S3 to Use Key"
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
          ArnLike = {
            "aws:SourceArn" = "arn:aws:s3:::${data.aws_s3_bucket.certificate_bucket.bucket}"
          }
        }
      }
    ]
  })

  tags = {
    Name        = "certificate-management-key"
    Environment = "production"
  }
}

# KMS Key Alias
resource "aws_kms_alias" "certificate_management" {
  name          = "alias/certificate-management-key"
  target_key_id = aws_kms_key.certificate_management.key_id
}
