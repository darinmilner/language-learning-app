variable "aws_region" {
  type        = string
  default     = "us-east-1"
  description = "AWS Deployment Region"
}

variable "certificate_bucket" {
  description = "S3 bucket for storing certificates"
  type        = string
}
