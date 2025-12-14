locals {
  azs           = data.aws_availability_zones.azs.names
  http_port     = "80"
  http_protocol = "HTTP"
}