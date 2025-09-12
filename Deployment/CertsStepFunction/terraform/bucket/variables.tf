variable "domain" {
  description = "Domain name for certificate management"
  type        = string
  default     = "example.com"
}

variable "certificate_bucket" {
  description = "S3 bucket for storing certificates"
  type        = string
}
