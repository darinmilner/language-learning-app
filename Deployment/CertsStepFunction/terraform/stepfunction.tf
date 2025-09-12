
# Step Function definition
resource "aws_sfn_state_machine" "certificate_manager" {
  name     = "certificate_manager"
  role_arn = aws_iam_role.step_function_role.arn

  definition = <<DEFINITION
{
  "Comment": "SSL Certificate Management Workflow",
  "StartAt": "CheckCertificate",
  "States": {
    "CheckCertificate": {
      "Type": "Task",
      "Resource": "${aws_lambda_function.check_certificate.arn}",
      "Next": "CertificateExpired?",
      "Parameters": {
        "domain.$": "$.domain"
      }
    },
    "CertificateExpired?": {
      "Type": "Choice",
      "Choices": [
        {
          "Variable": "$.expired",
          "BooleanEquals": true,
          "Next": "GenerateCertificate"
        }
      ],
      "Default": "Success"
    },
    "GenerateCertificate": {
      "Type": "Task",
      "Resource": "${aws_lambda_function.generate_certificate.arn}",
      "Next": "ReplaceCertificate",
      "Parameters": {
        "domain.$": "$.domain"
      }
    },
    "ReplaceCertificate": {
      "Type": "Task",
      "Resource": "${aws_lambda_function.replace_certificate.arn}",
      "End": true,
      "Parameters": {
        "domain.$": "$.domain",
        "certificate_arn.$": "$.certificate_arn"
      }
    },
    "Success": {
      "Type": "Succeed"
    }
  }
}
DEFINITION
}

# EventBridge rule
resource "aws_cloudwatch_event_rule" "weekly_cert_check" {
  name                = "weekly-certificate-check"
  description         = "Trigger certificate check every week"
  schedule_expression = "rate(7 days)"
}

resource "aws_cloudwatch_event_target" "trigger_step_function" {
  rule     = aws_cloudwatch_event_rule.weekly_cert_check.name
  arn      = aws_sfn_state_machine.certificate_manager.arn
  role_arn = aws_iam_role.eventbridge_role.arn
}