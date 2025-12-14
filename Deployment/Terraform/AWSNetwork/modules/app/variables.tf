variable "ecr_repository_name" {
  description = "Name of the ECR repository"
  type        = string
}

variable "app_path" {
  description = "App Path"
  type        = string
}

variable "image_version" {
  description = "Image Version"
  type        = string
}

variable "app_name" {
  description = "App Name"
  type = string 
}

variable "port" {
  description = "App Port Number"
  type = number
}

variable "execution_role_arn" {
  description = "ECS execution role"
  type = string
}

variable "is_public" {
  description = "Public IP for ECS service"
  type = bool
  default = true
}

variable "subnet_ids" {
  description = "Subnets for ECS service"
  type = list(string)
}

variable "ecs_cluster_id" {
  description = "ECS cluster id"
  type = string 
}

variable "ecs_security_group_id" {
  description = "ECS security group id"
  type = string 
}
