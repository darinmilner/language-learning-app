output "ecs_execution_role" {
  value = aws_iam_role.ecs_execution_role.arn 
}

output "subnet_ids" {
  value = [for i in aws_aws_subnet.public_subnet : i.id]
}

output "ecs_security_group_id" {
  value = aws_security_group.ecs_service.id
}

output "ecs_cluster_id" {
  value = aws_ecs_cluster.ecs_cluster.id 
}