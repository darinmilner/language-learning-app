provider "aws" {
  region = var.region
}

resource "aws_s3_bucket" "app_bucket" {
  bucket = var.bucket_name

  tags = {
    CreatedBy = "Jenkins/Terraform"
    Environment = "Dev"
  }
}
