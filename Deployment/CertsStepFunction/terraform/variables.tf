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

# Notification Configuration
variable "enable_sns_notifications" {
  description = "Enable SNS-based notifications"
  type        = bool
  default     = true
}

variable "notification_emails" {
  description = "List of email addresses to subscribe to SNS notifications"
  type        = list(string)
  default     = ["admin@example.com"]

  validation {
    condition = alltrue([
      for email in var.notification_emails : can(regex("^[^@]+@[^@]+\\.[^@]+$", email))
    ])
    error_message = "All notification emails must be valid email addresses."
  }
}

variable "env" {
  description = "Environment name for resource tagging"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.env)
    error_message = "Environment must be one of: development, staging, production."
  }
}