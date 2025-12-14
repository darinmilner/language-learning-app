variable "region" {
  type    = string
  default = "us-east-1"
}

variable "num_subnets" {
  description = "Number of subnets to deploy"
  type        = number
  default     = 2
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "beta"
}
