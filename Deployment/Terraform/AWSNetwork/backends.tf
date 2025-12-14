# terraform {
#   cloud {
#     organization = "tf-2025-examprep"

#     workspaces {
#       name = "aws-ecs"
#     }
#   }
# }

provider "aws" {
  region = var.region
}