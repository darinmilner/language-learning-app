import json
import logging
import os
from datetime import datetime, timezone

import boto3

# Constants
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_RETENTION_DAYS = 30
NOTIFICATION_TYPES = {
    "NO_EXPIRING": "no_expiring_certificates",
    "CERTIFICATES_UPDATED": "certificates_updated",
    "GENERAL": "general",
    "GENERATION_FAILURE": "generation_failure",
    "REPLACEMENT_FAILURE": "replacement_failure"
}
STATUS_CODES = {
    "SNS_DISABLED": "SNS_DISABLED",
    "PROCESSED": "PROCESSED",
    "ERROR": "ERROR",
    "SNS_SENT": "SNS_SENT",
    "SNS_FAILED": "SNS_FAILED",
    "LAMBDA_SUCCESS": "LAMBDA_SUCCESS",
    "LAMBDA_FAILED": "LAMBDA_FAILED"
}
SNS_EVENT_SOURCE = "aws:sns"
EMAIL_SUBJECT_PREFIXES = {
    "no_expiring_certificates": "✅ SSL Certificate Check - No Expiring Certificates",
    "certificates_updated": "🔄 SSL Certificate Update - Certificates Renewed",
    "generation_failure": "❌ SSL Certificate Error - Generation Failed",
    "replacement_failure": "❌ SSL Certificate Error - Replacement Failed",
    "general": "ℹ️ SSL Certificate Management Notification"
}

# Initialize AWS clients
sns = boto3.client("sns")
s3 = boto3.client("s3")

# Environment variables
sns_topic_arn = os.environ.get("SNS_TOPIC_ARN")
bucket_name = os.environ.get("S3_BUCKET")
log_level = os.environ.get("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()

# Configure logging
logger = logging.getLogger()
logger.setLevel(getattr(logging, log_level, logging.INFO))


def get_current_timestamp():
    """Get current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def lambda_handler(event, context):
    """
    Lambda handler for processing certificate notifications via SNS.
    
    Args:
        event: Lambda event containing notification data or SNS records
        context: Lambda context object
    
    Returns:
        dict: Processing status and results
    """
    logger.info("Processing certificate notification via SNS")
    logger.debug("Event: %s", event)

    # Check if SNS is enabled
    if not sns_topic_arn:
        logger.info("SNS notifications are disabled - no topic ARN provided")
        return {"status": STATUS_CODES["SNS_DISABLED"]}

    try:
        # Process SNS messages if event is from SNS
        if is_sns_event(event):
            return process_sns_messages(event["Records"])

        # Process direct invocation from Step Function
        return send_sns_notification(event)

    except (ValueError, KeyError, json.JSONDecodeError) as specific_error:
        logger.error("Specific error processing notification: %s", str(specific_error))
        return {"status": STATUS_CODES["ERROR"], "error": str(specific_error)}
    except Exception as unexpected_error:  # pylint: disable=broad-except
        logger.error("Unexpected error processing notification: %s", str(unexpected_error), exc_info=True)
        return {"status": STATUS_CODES["ERROR"], "error": "An unexpected error occurred"}


def is_sns_event(event):
    """Check if the event is from SNS."""
    return "Records" in event and event["Records"][0].get("EventSource") == SNS_EVENT_SOURCE


def process_sns_messages(records):
    """Process messages from SNS topic."""
    logger.info("Processing %d SNS messages", len(records))
    results = []

    for record in records:
        try:
            sns_message = json.loads(record["Sns"]["Message"])
            result = process_notification_message(sns_message)
            results.append(result)
        except json.JSONDecodeError as json_error:
            logger.error("JSON decode error in SNS message: %s", str(json_error))
            results.append({"status": STATUS_CODES["ERROR"], "error": "Invalid JSON in SNS message"})
        except Exception as message_error:  # pylint: disable=broad-except
            logger.error("Error processing SNS message: %s", str(message_error))
            results.append({"status": STATUS_CODES["ERROR"], "error": str(message_error)})

    return {"status": STATUS_CODES["PROCESSED"], "results": results}


def process_notification_message(message_data):
    """
    Process notification message and log appropriate information.
    
    Args:
        message_data (dict): Notification message data
    
    Returns:
        dict: Processing status
    """
    notification_type = message_data.get("notification_type", NOTIFICATION_TYPES["GENERAL"])
    
    if notification_type == NOTIFICATION_TYPES["NO_EXPIRING"]:
        return process_no_expiring_notification(message_data)
        
    elif notification_type == NOTIFICATION_TYPES["CERTIFICATES_UPDATED"]:
        return process_certificates_updated_notification(message_data)
        
    elif notification_type == NOTIFICATION_TYPES["GENERATION_FAILURE"]:
        return process_generation_failure_notification(message_data)
        
    elif notification_type == NOTIFICATION_TYPES["REPLACEMENT_FAILURE"]:
        return process_replacement_failure_notification(message_data)
    
    else:
        return process_general_notification(message_data)


def process_no_expiring_notification(message_data):
    """Process no expiring certificates notification."""
    domains_checked = message_data.get('domains_checked', [])
    domain_list = ', '.join([d.get('domain', 'Unknown') for d in domains_checked])
    
    logger.info(
        "No expiring certificates found for domains: %s", 
        domain_list
    )
    
    return {
        "status": STATUS_CODES["PROCESSED"], 
        "notification_type": NOTIFICATION_TYPES["NO_EXPIRING"],
        "domains_checked": len(domains_checked)
    }


def process_certificates_updated_notification(message_data):
    """Process certificates updated notification."""
    certificates = message_data.get("certificates_updated", [])
    
    logger.info(
        "Successfully updated %d certificates", 
        len(certificates)
    )
    
    for cert in certificates:
        logger.info(
            "Updated certificate - Domain: %s, New ARN: %s, Expiration: %s",
            cert.get('domain', 'Unknown'),
            cert.get('new_certificate_arn', 'N/A'),
            cert.get('expiration_date', 'N/A')
        )
        
        if not cert.get('old_certificate_deleted', False):
            logger.warning(
                "Old certificate not deleted for domain: %s, Error: %s",
                cert.get('domain', 'Unknown'),
                cert.get('deletion_error', 'Unknown error')
            )
    
    return {
        "status": STATUS_CODES["PROCESSED"],
        "notification_type": NOTIFICATION_TYPES["CERTIFICATES_UPDATED"],
        "certificates_updated": len(certificates)
    }


def process_generation_failure_notification(message_data):
    """Process certificate generation failure notification."""
    domain = message_data.get('domain', 'Unknown')
    error_details = message_data.get('error_details', 'No error details provided')
    
    logger.error(
        "Certificate generation failed for domain: %s, Error: %s",
        domain, error_details
    )
    
    return {
        "status": STATUS_CODES["PROCESSED"],
        "notification_type": NOTIFICATION_TYPES["GENERATION_FAILURE"],
        "domain": domain,
        "error": error_details
    }


def process_replacement_failure_notification(message_data):
    """Process certificate replacement failure notification."""
    domain = message_data.get('domain', 'Unknown')
    error_details = message_data.get('error_details', 'No error details provided')
    
    logger.error(
        "Certificate replacement failed for domain: %s, Error: %s", 
        domain, error_details
    )
    
    return {
        "status": STATUS_CODES["PROCESSED"],
        "notification_type": NOTIFICATION_TYPES["REPLACEMENT_FAILURE"],
        "domain": domain,
        "error": error_details
    }


def process_general_notification(message_data):
    """Process general notification."""
    message = message_data.get('message', 'No message provided')
    severity = message_data.get('severity', 'info')
    
    log_method = logger.info
    if severity == 'high':
        log_method = logger.error
    elif severity == 'medium':
        log_method = logger.warning
        
    log_method("General notification: %s", message)
    
    return {
        "status": STATUS_CODES["PROCESSED"],
        "notification_type": NOTIFICATION_TYPES["GENERAL"],
        "message": message,
        "severity": severity
    }


def send_sns_notification(notification_data):
    """
    Send notification to SNS topic.
    
    Args:
        notification_data (dict): Notification data to send to SNS
    
    Returns:
        dict: SNS sending status
    """
    logger.info("Sending certificate notification to SNS")

    try:
        message_attributes = create_sns_message_attributes(notification_data)
        message_body = create_sns_message_body(notification_data)
        subject = create_sns_subject(notification_data)
        
        response = sns.publish(
            TopicArn=sns_topic_arn,
            Message=message_body,
            MessageAttributes=message_attributes,
            Subject=subject
        )

        message_id = response["MessageId"]
        logger.info("Notification sent to SNS successfully: %s", message_id)
        return {
            "status": STATUS_CODES["SNS_SENT"], 
            "message_id": message_id,
            "subject": subject
        }

    except sns.exceptions.NotFoundException as not_found_error:
        logger.error("SNS topic not found: %s", str(not_found_error))
        return {
            "status": STATUS_CODES["SNS_FAILED"], 
            "error": f"SNS topic not found: {str(not_found_error)}"
        }
    except sns.exceptions.InvalidParameterException as param_error:
        logger.error("Invalid SNS parameters: %s", str(param_error))
        return {
            "status": STATUS_CODES["SNS_FAILED"], 
            "error": f"Invalid SNS parameters: {str(param_error)}"
        }
    except Exception as sns_error:  # pylint: disable=broad-except
        logger.error("Error sending to SNS: %s", str(sns_error))
        return {
            "status": STATUS_CODES["SNS_FAILED"], 
            "error": f"SNS send failed: {str(sns_error)}"
        }


def create_sns_message_attributes(notification_data):
    """
    Create SNS message attributes for filtering.
    
    Args:
        notification_data (dict): Notification data
    
    Returns:
        dict: SNS message attributes
    """
    notification_type = notification_data.get(
        "notification_type", 
        NOTIFICATION_TYPES["GENERAL"]
    )
    
    attributes = {
        "NotificationType": {
            "DataType": "String",
            "StringValue": notification_type
        },
        "Domain": {
            "DataType": "String",
            "StringValue": notification_data.get("domain", "multiple")
        },
        "Timestamp": {
            "DataType": "String",
            "StringValue": get_current_timestamp()
        },
        "Source": {
            "DataType": "String",
            "StringValue": "certificate-management-system"
        }
    }
    
    # Add severity attribute for error notifications
    severity = notification_data.get("severity", "info")
    if severity in ["high", "medium"]:
        attributes["Severity"] = {
            "DataType": "String",
            "StringValue": severity
        }
    
    return attributes


def create_sns_message_body(notification_data):
    """
    Create formatted SNS message body.
    
    Args:
        notification_data (dict): Notification data
    
    Returns:
        str: JSON-formatted message body
    """
    notification_type = notification_data.get(
        "notification_type", 
        NOTIFICATION_TYPES["GENERAL"]
    )
    
    base_message = {
        "notification_type": notification_type,
        "timestamp": get_current_timestamp(),
        "source": "certificate-management-system",
        "workflow_status": "completed"
    }
    
    # Add type-specific fields
    if notification_type == NOTIFICATION_TYPES["NO_EXPIRING"]:
        base_message.update({
            "message": notification_data.get("message", "No expiring certificates found"),
            "domains_checked": notification_data.get("domains_checked", []),
            "certificate_status": notification_data.get("certificate_status", "valid"),
            "check_time": notification_data.get("check_time", get_current_timestamp())
        })
        
    elif notification_type == NOTIFICATION_TYPES["CERTIFICATES_UPDATED"]:
        base_message.update({
            "message": notification_data.get("message", "Certificates successfully updated"),
            "certificates_updated": notification_data.get("certificates_updated", []),
            "transaction_id": notification_data.get("transaction_id", "N/A"),
            "update_time": notification_data.get("update_time", get_current_timestamp()),
            "s3_location": notification_data.get("s3_location", "N/A"),
            "workflow_status": "success"
        })
        
    elif notification_type == NOTIFICATION_TYPES["GENERATION_FAILURE"]:
        base_message.update({
            "message": notification_data.get("message", "Certificate generation failed"),
            "error_details": notification_data.get("error_details", "Unknown error"),
            "transaction_id": notification_data.get("transaction_id", "N/A"),
            "error_time": notification_data.get("error_time", get_current_timestamp()),
            "severity": notification_data.get("severity", "high"),
            "workflow_status": "failed"
        })
        
    elif notification_type == NOTIFICATION_TYPES["REPLACEMENT_FAILURE"]:
        base_message.update({
            "message": notification_data.get("message", "Certificate replacement failed"),
            "error_details": notification_data.get("error_details", "Unknown error"),
            "transaction_id": notification_data.get("transaction_id", "N/A"),
            "error_time": notification_data.get("error_time", get_current_timestamp()),
            "severity": notification_data.get("severity", "high"),
            "workflow_status": "failed"
        })
        
    else:
        base_message.update({
            "message": notification_data.get("message", "Certificate management notification"),
            "transaction_id": notification_data.get("transaction_id", "N/A"),
            "severity": notification_data.get("severity", "info")
        })
    
    return json.dumps(base_message, indent=2)


def create_sns_subject(notification_data):
    """
    Create SNS message subject based on notification type.
    
    Args:
        notification_data (dict): Notification data
    
    Returns:
        str: Message subject
    """
    notification_type = notification_data.get(
        "notification_type", 
        NOTIFICATION_TYPES["GENERAL"]
    )
    
    domain = notification_data.get("domain", "Multiple Domains")
    severity = notification_data.get("severity", "info")
    
    subject_prefix = EMAIL_SUBJECT_PREFIXES.get(
        notification_type,
        EMAIL_SUBJECT_PREFIXES["general"]
    )
    
    subject = f"{subject_prefix} - {domain}"
    
    # Add urgency indicator for high severity
    if severity == "high":
        subject = f"🚨 URGENT: {subject}"
    elif severity == "medium":
        subject = f"⚠️  WARNING: {subject}"
    
    return subject


def send_to_sns_from_other_lambdas(notification_data):
    """
    Send notification to SNS topic (for use by other Lambdas).
    
    Args:
        notification_data (dict): Notification data to send to SNS
    
    Returns:
        dict: SNS sending status
    """
    if not sns_topic_arn:
        logger.debug("SNS topic ARN not available - skipping SNS send")
        return {"status": STATUS_CODES["SNS_DISABLED"]}
    
    return send_sns_notification(notification_data)
