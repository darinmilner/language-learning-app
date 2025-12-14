# root main.tf
module "infra" {
  source      = "./modules/infra"
  vpc_cidr    = "10.0.0.0/16"
  num_subnets = var.num_subnets
  environment = var.environment
  allowed_ips = ["0.0.0.0/0"]
}

module "app" {
  source              = "./modules/app"
  ecr_repository_name = "ui"
  app_path            = "ui"
  image_version       = "1.0.0"
  app_name = "ui"
  port = 80
  execution_role_arn = module.infra.execution_role_arn 
  subnet_ids = module.infra.subnet_ids
  ecs_security_group_id = module.infra.ecs_security_group_id
  ecs_cluster_id = module.infra.ecs_cluster_id
}