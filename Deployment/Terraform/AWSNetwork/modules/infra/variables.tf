variable "vpc_cidr" {
  type        = string
  description = "VPC Cidr Block"
}

variable "num_subnets" {
  type        = number
  description = "Num subnets"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "allowed_ips" {
  description = "Allowed IP addresses"
  type        = set(string)
}
