variable "aws_region" {
  type        = string
  default     = "us-east-1"
  description = "AWS Deployment Region"
}

variable "timeout" {
  type    = number
  default = 300
}

variable "certbot_email" {
  type    = string
  default = "example@yourmail.com"
}

variable "runtime" {
  type    = string
  default = "python3.13"
}

variable "bucket" {
  description = "S3 bucket for storing certificates"
  type        = string
  default     = "your-bucket-name-here"
}

variable "domain" {
  description = "Domain for checking the certificates"
  type        = string
  default     = "yourdomain.com"
}

variable "log_level" {
  description = "Log Level for Lambda logging"
  type        = string
  default     = "INFO"

  validation {
    condition     = contains(["DEBUG", "INFO", "WARNING", "ERROR"], var.log_level)
    error_message = "Log level must be one of: DEBUG, INFO, WARNING, ERROR."
  }
}