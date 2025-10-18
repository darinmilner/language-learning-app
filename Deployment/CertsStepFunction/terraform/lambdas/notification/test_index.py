import json
import os
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

import index


class TestNotificationLambda:
    """Test suite for notification Lambda function."""

    @pytest.fixture
    def setup_env(self):
        """Set up environment variables for testing."""
        with patch.dict(os.environ, {
            "SNS_TOPIC_ARN": "arn:aws:sns:us-east-1:123456789012:test-topic",
            "S3_BUCKET": "test-bucket",
            "LOG_LEVEL": "INFO"
        }):
            yield

    @pytest.fixture
    def mock_aws_clients(self):
        """Mock AWS clients."""
        with patch("index.sns") as mock_sns, patch("index.s3") as mock_s3:
            yield {"sns": mock_sns, "s3": mock_s3}

    @pytest.fixture
    def sample_sns_event(self):
        """Return sample SNS event."""
        return {
            "Records": [
                {
                    "EventSource": "aws:sns",
                    "Sns": {
                        "Message": json.dumps({
                            "notification_type": "no_expiring_certificates",
                            "domains_checked": [{"domain": "example.com"}]
                        })
                    }
                }
            ]
        }

    @pytest.fixture
    def sample_direct_event(self):
        """Return sample direct invocation event."""
        return {
            "notification_type": "certificates_updated",
            "domain": "example.com",
            "transaction_id": "test-transaction-123"
        }

    def test_lambda_handler_sns_disabled(self):
        """Test Lambda handler when SNS is disabled."""
        with patch.dict(os.environ, {}, clear=True):
            result = index.lambda_handler({}, {})
        
        assert result["status"] == index.STATUS_CODES["SNS_DISABLED"]

    def test_lambda_handler_sns_event(
        self, setup_env, mock_aws_clients, sample_sns_event
    ):
        """Test Lambda handler with SNS event."""
        result = index.lambda_handler(sample_sns_event, {})
        
        assert result["status"] == index.STATUS_CODES["PROCESSED"]
        assert "results" in result

    def test_lambda_handler_direct_invocation(
        self, setup_env, mock_aws_clients, sample_direct_event
    ):
        """Test Lambda handler with direct invocation."""
        mock_aws_clients["sns"].publish.return_value = {"MessageId": "test-message-id"}
        
        result = index.lambda_handler(sample_direct_event, {})
        
        assert result["status"] == index.STATUS_CODES["SNS_SENT"]
        mock_aws_clients["sns"].publish.assert_called_once()

    def test_lambda_handler_json_decode_error(
        self, setup_env, mock_aws_clients
    ):
        """Test Lambda handler with invalid JSON in SNS event."""
        invalid_sns_event = {
            "Records": [
                {
                    "EventSource": "aws:sns",
                    "Sns": {
                        "Message": "invalid-json{"
                    }
                }
            ]
        }
        
        result = index.lambda_handler(invalid_sns_event, {})
        
        assert result["status"] == index.STATUS_CODES["PROCESSED"]
        assert result["results"][0]["status"] == index.STATUS_CODES["ERROR"]

    def test_lambda_handler_unexpected_error(
        self, setup_env, mock_aws_clients
    ):
        """Test Lambda handler with unexpected error."""
        with patch("index.is_sns_event", side_effect=Exception("Unexpected error")):
            result = index.lambda_handler({}, {})
        
        assert result["status"] == index.STATUS_CODES["ERROR"]


class TestHelperFunctions:
    """Test suite for helper functions."""

    def test_get_current_timestamp(self):
        """Test timestamp generation."""
        timestamp = index.get_current_timestamp()
        
        # Should be a valid ISO format string
        parsed_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        assert isinstance(parsed_time, datetime)

    def test_is_sns_event_true(self):
        """Test SNS event detection with valid SNS event."""
        event = {
            "Records": [
                {
                    "EventSource": "aws:sns"
                }
            ]
        }
        
        assert index.is_sns_event(event) is True

    def test_is_sns_event_false(self):
        """Test SNS event detection with non-SNS event."""
        event = {
            "Records": [
                {
                    "EventSource": "aws:sqs"
                }
            ]
        }
        
        assert index.is_sns_event(event) is False

    def test_is_sns_event_no_records(self):
        """Test SNS event detection with no records."""
        event = {}
        
        assert index.is_sns_event(event) is False


class TestProcessSnsMessages:
    """Test suite for process_sns_messages function."""

    def test_process_sns_messages_success(self):
        """Test successful SNS message processing."""
        records = [
            {
                "Sns": {
                    "Message": json.dumps({
                        "notification_type": "no_expiring_certificates",
                        "domains_checked": [{"domain": "example.com"}]
                    })
                }
            }
        ]
        
        result = index.process_sns_messages(records)
        
        assert result["status"] == index.STATUS_CODES["PROCESSED"]
        assert len(result["results"]) == 1
        assert result["results"][0]["status"] == index.STATUS_CODES["PROCESSED"]

    def test_process_sns_messages_multiple_records(self):
        """Test processing multiple SNS messages."""
        records = [
            {
                "Sns": {
                    "Message": json.dumps({
                        "notification_type": "no_expiring_certificates",
                        "domains_checked": [{"domain": "example.com"}]
                    })
                }
            },
            {
                "Sns": {
                    "Message": json.dumps({
                        "notification_type": "certificates_updated",
                        "certificates_updated": [{"domain": "example.com"}]
                    })
                }
            }
        ]
        
        result = index.process_sns_messages(records)
        
        assert result["status"] == index.STATUS_CODES["PROCESSED"]
        assert len(result["results"]) == 2

    def test_process_sns_messages_json_error(self):
        """Test SNS message processing with JSON error."""
        records = [
            {
                "Sns": {
                    "Message": "invalid-json{"
                }
            }
        ]
        
        result = index.process_sns_messages(records)
        
        assert result["results"][0]["status"] == index.STATUS_CODES["ERROR"]


class TestProcessNotificationMessage:
    """Test suite for process_notification_message function."""

    def test_process_no_expiring_notification(self):
        """Test processing no expiring certificates notification."""
        message_data = {
            "notification_type": "no_expiring_certificates",
            "domains_checked": [
                {"domain": "example.com"},
                {"domain": "test.com"}
            ]
        }
        
        result = index.process_notification_message(message_data)
        
        assert result["status"] == index.STATUS_CODES["PROCESSED"]
        assert result["notification_type"] == index.NOTIFICATION_TYPES["NO_EXPIRING"]
        assert result["domains_checked"] == 2

    def test_process_certificates_updated_notification(self):
        """Test processing certificates updated notification."""
        message_data = {
            "notification_type": "certificates_updated",
            "certificates_updated": [
                {
                    "domain": "example.com",
                    "new_certificate_arn": "arn:aws:acm:new-cert",
                    "expiration_date": "2024-12-31T23:59:59",
                    "old_certificate_deleted": True
                }
            ]
        }
        
        result = index.process_notification_message(message_data)
        
        assert result["status"] == index.STATUS_CODES["PROCESSED"]
        assert result["notification_type"] == index.NOTIFICATION_TYPES["CERTIFICATES_UPDATED"]
        assert result["certificates_updated"] == 1

    def test_process_generation_failure_notification(self):
        """Test processing generation failure notification."""
        message_data = {
            "notification_type": "generation_failure",
            "domain": "example.com",
            "error_details": "Certbot DNS validation failed"
        }
        
        result = index.process_notification_message(message_data)
        
        assert result["status"] == index.STATUS_CODES["PROCESSED"]
        assert result["notification_type"] == index.NOTIFICATION_TYPES["GENERATION_FAILURE"]
        assert result["domain"] == "example.com"

    def test_process_replacement_failure_notification(self):
        """Test processing replacement failure notification."""
        message_data = {
            "notification_type": "replacement_failure",
            "domain": "example.com",
            "error_details": "ACM import failed"
        }
        
        result = index.process_notification_message(message_data)
        
        assert result["status"] == index.STATUS_CODES["PROCESSED"]
        assert result["notification_type"] == index.NOTIFICATION_TYPES["REPLACEMENT_FAILURE"]
        assert result["domain"] == "example.com"

    def test_process_general_notification(self):
        """Test processing general notification."""
        message_data = {
            "notification_type": "general",
            "message": "Test notification",
            "severity": "info"
        }
        
        result = index.process_notification_message(message_data)
        
        assert result["status"] == index.STATUS_CODES["PROCESSED"]
        assert result["notification_type"] == index.NOTIFICATION_TYPES["GENERAL"]
        assert result["message"] == "Test notification"

    def test_process_unknown_notification_type(self):
        """Test processing unknown notification type."""
        message_data = {
            "notification_type": "unknown_type",
            "message": "Unknown notification"
        }
        
        result = index.process_notification_message(message_data)
        
        assert result["status"] == index.STATUS_CODES["PROCESSED"]
        assert result["notification_type"] == index.NOTIFICATION_TYPES["GENERAL"]


class TestSendSnsNotification:
    """Test suite for send_sns_notification function."""

    @pytest.fixture
    def setup_env(self):
        """Set up environment variables."""
        with patch.dict(os.environ, {
            "SNS_TOPIC_ARN": "arn:aws:sns:us-east-1:123456789012:test-topic"
        }):
            yield

    @pytest.fixture
    def mock_sns(self):
        """Mock SNS client."""
        with patch("index.sns") as mock_sns:
            yield mock_sns

    def test_send_sns_notification_success(self, setup_env, mock_sns):
        """Test successful SNS notification sending."""
        mock_sns.publish.return_value = {"MessageId": "test-message-id"}
        
        notification_data = {
            "notification_type": "no_expiring_certificates",
            "domain": "example.com"
        }
        
        result = index.send_sns_notification(notification_data)
        
        assert result["status"] == index.STATUS_CODES["SNS_SENT"]
        assert result["message_id"] == "test-message-id"
        mock_sns.publish.assert_called_once()

    def test_send_sns_notification_topic_not_found(self, setup_env, mock_sns):
        """Test SNS notification with topic not found error."""
        mock_sns.publish.side_effect = mock_sns.exceptions.NotFoundException(
            error_response={"Error": {"Code": "NotFound"}},
            operation_name="Publish"
        )
        
        result = index.send_sns_notification({})
        
        assert result["status"] == index.STATUS_CODES["SNS_FAILED"]
        assert "not found" in result["error"].lower()

    def test_send_sns_notification_invalid_parameters(self, setup_env, mock_sns):
        """Test SNS notification with invalid parameters error."""
        mock_sns.publish.side_effect = mock_sns.exceptions.InvalidParameterException(
            error_response={"Error": {"Code": "InvalidParameter"}},
            operation_name="Publish"
        )
        
        result = index.send_sns_notification({})
        
        assert result["status"] == index.STATUS_CODES["SNS_FAILED"]
        assert "invalid" in result["error"].lower()

    def test_send_sns_notification_generic_error(self, setup_env, mock_sns):
        """Test SNS notification with generic error."""
        mock_sns.publish.side_effect = Exception("Generic SNS error")
        
        result = index.send_sns_notification({})
        
        assert result["status"] == index.STATUS_CODES["SNS_FAILED"]
        assert "failed" in result["error"].lower()


class TestCreateSnsMessageAttributes:
    """Test suite for create_sns_message_attributes function."""

    def test_create_sns_message_attributes_basic(self):
        """Test basic SNS message attributes creation."""
        notification_data = {
            "notification_type": "no_expiring_certificates",
            "domain": "example.com"
        }
        
        attributes = index.create_sns_message_attributes(notification_data)
        
        assert "NotificationType" in attributes
        assert "Domain" in attributes
        assert "Timestamp" in attributes
        assert "Source" in attributes
        assert attributes["NotificationType"]["StringValue"] == "no_expiring_certificates"
        assert attributes["Domain"]["StringValue"] == "example.com"

    def test_create_sns_message_attributes_with_severity(self):
        """Test SNS message attributes with severity."""
        notification_data = {
            "notification_type": "generation_failure",
            "domain": "example.com",
            "severity": "high"
        }
        
        attributes = index.create_sns_message_attributes(notification_data)
        
        assert "Severity" in attributes
        assert attributes["Severity"]["StringValue"] == "high"

    def test_create_sns_message_attributes_default_domain(self):
        """Test SNS message attributes with default domain."""
        notification_data = {
            "notification_type": "general"
        }
        
        attributes = index.create_sns_message_attributes(notification_data)
        
        assert attributes["Domain"]["StringValue"] == "multiple"


class TestCreateSnsMessageBody:
    """Test suite for create_sns_message_body function."""

    def test_create_sns_message_body_no_expiring(self):
        """Test message body creation for no expiring certificates."""
        notification_data = {
            "notification_type": "no_expiring_certificates",
            "domains_checked": [{"domain": "example.com"}],
            "message": "All certificates valid"
        }
        
        message_body = index.create_sns_message_body(notification_data)
        message_data = json.loads(message_body)
        
        assert message_data["notification_type"] == "no_expiring_certificates"
        assert message_data["workflow_status"] == "completed"
        assert len(message_data["domains_checked"]) == 1

    def test_create_sns_message_body_certificates_updated(self):
        """Test message body creation for certificates updated."""
        notification_data = {
            "notification_type": "certificates_updated",
            "certificates_updated": [{"domain": "example.com"}],
            "transaction_id": "test-123",
            "s3_location": "s3://bucket/certificates/"
        }
        
        message_body = index.create_sns_message_body(notification_data)
        message_data = json.loads(message_body)
        
        assert message_data["notification_type"] == "certificates_updated"
        assert message_data["workflow_status"] == "success"
        assert message_data["transaction_id"] == "test-123"

    def test_create_sns_message_body_generation_failure(self):
        """Test message body creation for generation failure."""
        notification_data = {
            "notification_type": "generation_failure",
            "error_details": "DNS validation failed",
            "severity": "high"
        }
        
        message_body = index.create_sns_message_body(notification_data)
        message_data = json.loads(message_body)
        
        assert message_data["notification_type"] == "generation_failure"
        assert message_data["workflow_status"] == "failed"
        assert message_data["severity"] == "high"

    def test_create_sns_message_body_general(self):
        """Test message body creation for general notification."""
        notification_data = {
            "notification_type": "general",
            "message": "Test message",
            "severity": "info"
        }
        
        message_body = index.create_sns_message_body(notification_data)
        message_data = json.loads(message_body)
        
        assert message_data["notification_type"] == "general"
        assert message_data["message"] == "Test message"


class TestCreateSnsSubject:
    """Test suite for create_sns_subject function."""

    def test_create_sns_subject_no_expiring(self):
        """Test subject creation for no expiring certificates."""
        notification_data = {
            "notification_type": "no_expiring_certificates",
            "domain": "example.com"
        }
        
        subject = index.create_sns_subject(notification_data)
        
        assert "✅ SSL Certificate Check" in subject
        assert "example.com" in subject

    def test_create_sns_subject_certificates_updated(self):
        """Test subject creation for certificates updated."""
        notification_data = {
            "notification_type": "certificates_updated",
            "domain": "example.com"
        }
        
        subject = index.create_sns_subject(notification_data)
        
        assert "🔄 SSL Certificate Update" in subject
        assert "example.com" in subject

    def test_create_sns_subject_with_high_severity(self):
        """Test subject creation with high severity."""
        notification_data = {
            "notification_type": "generation_failure",
            "domain": "example.com",
            "severity": "high"
        }
        
        subject = index.create_sns_subject(notification_data)
        
        assert "🚨 URGENT:" in subject
        assert "❌ SSL Certificate Error" in subject

    def test_create_sns_subject_with_medium_severity(self):
        """Test subject creation with medium severity."""
        notification_data = {
            "notification_type": "general",
            "domain": "example.com",
            "severity": "medium"
        }
        
        subject = index.create_sns_subject(notification_data)
        
        assert "⚠️  WARNING:" in subject

    def test_create_sns_subject_default_domain(self):
        """Test subject creation with default domain."""
        notification_data = {
            "notification_type": "general"
        }
        
        subject = index.create_sns_subject(notification_data)
        
        assert "Multiple Domains" in subject


class TestSendToSnsFromOtherLambdas:
    """Test suite for send_to_sns_from_other_lambdas function."""

    def test_send_to_sns_from_other_lambdas_disabled(self):
        """Test SNS sending when disabled."""
        with patch.dict(os.environ, {}, clear=True):
            result = index.send_to_sns_from_other_lambdas({})
        
        assert result["status"] == index.STATUS_CODES["SNS_DISABLED"]

    def test_send_to_sns_from_other_lambdas_enabled(self):
        """Test SNS sending when enabled."""
        with patch.dict(os.environ, {"SNS_TOPIC_ARN": "test-topic"}):
            with patch("index.send_sns_notification") as mock_send:
                mock_send.return_value = {"status": "SNS_SENT"}
                
                result = index.send_to_sns_from_other_lambdas({})
        
        mock_send.assert_called_once_with({})
        assert result["status"] == "SNS_SENT"


class TestConstants:
    """Test suite for constants."""

    def test_notification_types(self):
        """Test notification types constants."""
        expected_types = {
            "NO_EXPIRING": "no_expiring_certificates",
            "CERTIFICATES_UPDATED": "certificates_updated",
            "GENERAL": "general",
            "GENERATION_FAILURE": "generation_failure",
            "REPLACEMENT_FAILURE": "replacement_failure"
        }
        
        assert index.NOTIFICATION_TYPES == expected_types

    def test_status_codes(self):
        """Test status codes constants."""
        expected_codes = {
            "SNS_DISABLED": "SNS_DISABLED",
            "PROCESSED": "PROCESSED",
            "ERROR": "ERROR",
            "SNS_SENT": "SNS_SENT",
            "SNS_FAILED": "SNS_FAILED",
            "LAMBDA_SUCCESS": "LAMBDA_SUCCESS",
            "LAMBDA_FAILED": "LAMBDA_FAILED"
        }
        
        assert index.STATUS_CODES == expected_codes

    def test_email_subject_prefixes(self):
        """Test email subject prefixes constants."""
        expected_prefixes = {
            "no_expiring_certificates": "✅ SSL Certificate Check - No Expiring Certificates",
            "certificates_updated": "🔄 SSL Certificate Update - Certificates Renewed",
            "generation_failure": "❌ SSL Certificate Error - Generation Failed",
            "replacement_failure": "❌ SSL Certificate Error - Replacement Failed",
            "general": "ℹ️ SSL Certificate Management Notification"
        }
        
        assert index.EMAIL_SUBJECT_PREFIXES == expected_prefixes
        