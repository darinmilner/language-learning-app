variable "region" {
  description = "AWS Region"
  type        = string
  default = "us-east-1"
}

variable "bucket_name" {
  description = "Name of the S3 bucket"
  type        = string
  default = "test-jenkins-bucket-05312025"
}
