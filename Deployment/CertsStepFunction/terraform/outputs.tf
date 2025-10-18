output "notification_lambda_arn" {
  description = "ARN of the notification Lambda function"
  value       = aws_lambda_function.notification.arn
}

output "sns_topic_arn" {
  description = "ARN of the SNS notification topic"
  value       = var.enable_sns_notifications ? aws_sns_topic.certificate_notifications[0].arn : "SNS_DISABLED"
}

output "sns_topic_name" {
  description = "Name of the SNS notification topic"
  value       = var.enable_sns_notifications ? aws_sns_topic.certificate_notifications[0].name : "SNS_DISABLED"
}

output "notification_subscriptions" {
  description = "Number of email subscriptions to SNS topic"
  value       = var.enable_sns_notifications ? length(var.notification_emails) : 0
}

output "notification_status" {
  description = "Status of notification system"
  value       = var.enable_sns_notifications ? "ENABLED" : "DISABLED"
}