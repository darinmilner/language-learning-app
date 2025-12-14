locals {
  ecr_url   = aws_ecr_repository.ecs_repo.repository_url
  ecr_token = data.aws_ecr_authorization_token.token
}