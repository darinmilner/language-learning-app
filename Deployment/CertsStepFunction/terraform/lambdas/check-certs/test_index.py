import json
import logging
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

# Import the module to test
import index


class TestCheckCertificateLambda:
    """Test suite for check certificate Lambda function."""

    @pytest.fixture
    def setup_env(self):
        """Set up environment variables for testing."""
        with patch.dict(os.environ, {
            "S3_BUCKET": "test-bucket",
            "LOG_LEVEL": "INFO"
        }):
            yield

    @pytest.fixture
    def mock_aws_clients(self):
        """Mock AWS clients."""
        with patch("index.s3") as mock_s3, patch("index.acm") as mock_acm:
            yield {"s3": mock_s3, "acm": mock_acm}

    @pytest.fixture
    def sample_event(self):
        """Return sample Lambda event."""
        return {"domain": "example.com"}

    @pytest.fixture
    def sample_certificate_data(self):
        """Return sample certificate data."""
        future_date = datetime.utcnow() + timedelta(days=60)
        return {
            "certificate_arn": "arn:aws:acm:us-east-1:123456789012:certificate/12345678",
            "detail": {
                "NotAfter": future_date,
                "Status": "ISSUED"
            }
        }

    @pytest.fixture
    def expired_certificate_data(self):
        """Return expired certificate data."""
        past_date = datetime.utcnow() - timedelta(days=1)
        return {
            "certificate_arn": "arn:aws:acm:us-east-1:123456789012:certificate/expired",
            "detail": {
                "NotAfter": past_date,
                "Status": "ISSUED"
            }
        }

    def test_lambda_handler_missing_bucket_name(self, sample_event):
        """Test Lambda handler raises error when S3_BUCKET is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="S3_BUCKET environment variable is required"):
                index.lambda_handler(sample_event, {})

    def test_lambda_handler_existing_valid_certificate(
        self, setup_env, mock_aws_clients, sample_event, sample_certificate_data
    ):
        """Test Lambda handler with existing valid certificate."""
        with patch("index.get_certificate_details", return_value=sample_certificate_data):
            result = index.lambda_handler(sample_event, {})

        assert result["expired"] is False
        assert result["domain"] == "example.com"
        assert "transaction_id" in result
        assert result["bucket_name"] == "test-bucket"

    def test_lambda_handler_existing_expired_certificate(
        self, setup_env, mock_aws_clients, sample_event, expired_certificate_data
    ):
        """Test Lambda handler with existing expired certificate."""
        with patch("index.get_certificate_details", return_value=expired_certificate_data):
            result = index.lambda_handler(sample_event, {})

        assert result["expired"] is True
        assert result["reason"] == "Certificate expired or expiring soon"

    def test_lambda_handler_no_certificate_found(
        self, setup_env, mock_aws_clients, sample_event
    ):
        """Test Lambda handler when no certificate is found."""
        with patch("index.get_certificate_details", return_value=None):
            result = index.lambda_handler(sample_event, {})

        assert result["expired"] is True
        assert result["reason"] == "No certificate found in ACM"

    def test_lambda_handler_exception(
        self, setup_env, mock_aws_clients, sample_event
    ):
        """Test Lambda handler when exception occurs."""
        with patch("index.get_certificate_details", side_effect=Exception("Test error")):
            with pytest.raises(Exception, match="Test error"):
                index.lambda_handler(sample_event, {})


class TestGetCertificateDetails:
    """Test suite for get_certificate_details function."""

    @pytest.fixture
    def mock_acm(self):
        """Mock ACM client."""
        with patch("index.acm") as mock_acm:
            yield mock_acm

    def test_get_certificate_details_found(self, mock_acm):
        """Test getting certificate details when certificate exists."""
        future_date = datetime.utcnow() + timedelta(days=60)
        mock_acm.list_certificates.return_value = {
            "CertificateSummaryList": [
                {
                    "CertificateArn": "arn:aws:acm:us-east-1:123456789012:certificate/12345678",
                    "DomainName": "example.com"
                }
            ]
        }
        mock_acm.describe_certificate.return_value = {
            "Certificate": {
                "NotAfter": future_date,
                "Status": "ISSUED"
            }
        }

        result = index.get_certificate_details("example.com")

        assert result is not None
        assert result["certificate_arn"] == "arn:aws:acm:us-east-1:123456789012:certificate/12345678"
        mock_acm.list_certificates.assert_called_once()
        mock_acm.describe_certificate.assert_called_once()

    def test_get_certificate_details_not_found(self, mock_acm):
        """Test getting certificate details when certificate doesn't exist."""
        mock_acm.list_certificates.return_value = {
            "CertificateSummaryList": []
        }

        result = index.get_certificate_details("example.com")

        assert result is None
        mock_acm.list_certificates.assert_called_once()

    def test_get_certificate_details_exception(self, mock_acm):
        """Test getting certificate details when ACM call fails."""
        mock_acm.list_certificates.side_effect = Exception("ACM error")

        with pytest.raises(Exception, match="ACM error"):
            index.get_certificate_details("example.com")


class TestIsCertificateExpired:
    """Test suite for is_certificate_expired function."""

    def test_certificate_valid(self):
        """Test certificate that is valid and not expiring soon."""
        future_date = datetime.utcnow() + timedelta(days=60)
        cert_detail = {"NotAfter": future_date}

        result = index.is_certificate_expired(cert_detail)

        assert result["is_expired"] is False
        assert result["is_expiring_soon"] is False

    def test_certificate_expired(self):
        """Test certificate that is expired."""
        past_date = datetime.utcnow() - timedelta(days=1)
        cert_detail = {"NotAfter": past_date}

        result = index.is_certificate_expired(cert_detail)

        assert result["is_expired"] is True
        assert result["is_expiring_soon"] is True

    def test_certificate_expiring_soon(self):
        """Test certificate that is expiring soon."""
        future_date = datetime.utcnow() + timedelta(days=15)
        cert_detail = {"NotAfter": future_date}

        result = index.is_certificate_expired(cert_detail)

        assert result["is_expired"] is False
        assert result["is_expiring_soon"] is True


class TestHandleExistingCertificate:
    """Test suite for handle_existing_certificate function."""

    @pytest.fixture
    def setup_env(self):
        """Set up environment variables."""
        with patch.dict(os.environ, {"S3_BUCKET": "test-bucket"}):
            yield

    @pytest.fixture
    def sample_certificate_data(self):
        """Return sample certificate data."""
        future_date = datetime.utcnow() + timedelta(days=60)
        return {
            "certificate_arn": "arn:aws:acm:us-east-1:123456789012:certificate/12345678",
            "detail": {
                "NotAfter": future_date,
                "Status": "ISSUED"
            }
        }

    def test_handle_existing_valid_certificate(
        self, setup_env, sample_certificate_data
    ):
        """Test handling valid certificate."""
        with patch("index.is_certificate_expired") as mock_is_expired, \
             patch("index.store_check_metadata") as mock_store_metadata:

            mock_is_expired.return_value = {
                "is_expired": False,
                "is_expiring_soon": False,
                "expiration_date": "2024-01-01T00:00:00"
            }

            result = index.handle_existing_certificate(
                sample_certificate_data, "example.com", "test-transaction"
            )

        assert result["expired"] is False
        assert result["certificate_arn"] == sample_certificate_data["certificate_arn"]
        mock_store_metadata.assert_called_once()

    def test_handle_existing_expired_certificate(
        self, setup_env, sample_certificate_data
    ):
        """Test handling expired certificate."""
        with patch("index.is_certificate_expired") as mock_is_expired, \
             patch("index.store_check_metadata") as mock_store_metadata:

            mock_is_expired.return_value = {
                "is_expired": True,
                "is_expiring_soon": True,
                "expiration_date": "2023-01-01T00:00:00"
            }

            result = index.handle_existing_certificate(
                sample_certificate_data, "example.com", "test-transaction"
            )

        assert result["expired"] is True
        assert result["reason"] == "Certificate expired or expiring soon"
        mock_store_metadata.assert_called_once()


class TestHandleMissingCertificate:
    """Test suite for handle_missing_certificate function."""

    @pytest.fixture
    def setup_env(self):
        """Set up environment variables."""
        with patch.dict(os.environ, {"S3_BUCKET": "test-bucket"}):
            yield

    def test_handle_missing_certificate(self, setup_env):
        """Test handling missing certificate."""
        with patch("index.store_check_metadata") as mock_store_metadata:
            result = index.handle_missing_certificate("example.com", "test-transaction")

        assert result["expired"] is True
        assert result["reason"] == "No certificate found in ACM"
        mock_store_metadata.assert_called_once_with(
            "test-transaction", "example.com", None, {}
        )


class TestStoreCheckMetadata:
    """Test suite for store_check_metadata function."""

    @pytest.fixture
    def setup_env(self):
        """Set up environment variables."""
        with patch.dict(os.environ, {"S3_BUCKET": "test-bucket"}):
            yield

    @pytest.fixture
    def mock_s3(self):
        """Mock S3 client."""
        with patch("index.s3") as mock_s3:
            yield mock_s3

    def test_store_check_metadata_with_certificate(
        self, setup_env, mock_s3, sample_certificate_data
    ):
        """Test storing metadata with certificate data."""
        check_result = {
            "is_expired": False,
            "is_expiring_soon": False,
            "expiration_date": "2024-01-01T00:00:00"
        }

        index.store_check_metadata(
            "test-transaction", "example.com", sample_certificate_data, check_result
        )

        mock_s3.put_object.assert_called_once()
        call_args = mock_s3.put_object.call_args
        assert call_args[1]["Bucket"] == "test-bucket"
        assert "check_metadata.json" in call_args[1]["Key"]

    def test_store_check_metadata_without_certificate(
        self, setup_env, mock_s3
    ):
        """Test storing metadata without certificate data."""
        check_result = {}

        index.store_check_metadata(
            "test-transaction", "example.com", None, check_result
        )

        mock_s3.put_object.assert_called_once()
        call_args = mock_s3.put_object.call_args
        body = json.loads(call_args[1]["Body"])
        assert body["certificate_arn"] is None
        assert body["certificate_status"] == "NOT_FOUND"


class TestStoreErrorMetadata:
    """Test suite for store_error_metadata function."""

    @pytest.fixture
    def setup_env(self):
        """Set up environment variables."""
        with patch.dict(os.environ, {"S3_BUCKET": "test-bucket"}):
            yield

    @pytest.fixture
    def mock_s3(self):
        """Mock S3 client."""
        with patch("index.s3") as mock_s3:
            yield mock_s3

    def test_store_error_metadata(self, setup_env, mock_s3):
        """Test storing error metadata."""
        index.store_error_metadata("test-transaction", "example.com", "Test error")

        mock_s3.put_object.assert_called_once()
        call_args = mock_s3.put_object.call_args
        assert call_args[1]["Bucket"] == "test-bucket"
        assert "errormetadata.json" in call_args[1]["Key"]

        body = json.loads(call_args[1]["Body"])
        assert body["error_message"] == "Test error"
        assert body["transaction_id"] == "test-transaction"


class TestCreateResponse:
    """Test suite for create_response function."""

    @pytest.fixture
    def setup_env(self):
        """Set up environment variables."""
        with patch.dict(os.environ, {"S3_BUCKET": "test-bucket"}):
            yield

    def test_create_response_minimal(self, setup_env):
        """Test creating response with minimal parameters."""
        result = index.create_response(
            expired=False,
            domain="example.com",
            transaction_id="test-transaction"
        )

        assert result == {
            "expired": False,
            "domain": "example.com",
            "transaction_id": "test-transaction",
            "bucket_name": "test-bucket"
        }

    def test_create_response_full(self, setup_env):
        """Test creating response with all parameters."""
        result = index.create_response(
            expired=True,
            domain="example.com",
            transaction_id="test-transaction",
            certificate_arn="test-arn",
            expiration_date="2023-01-01T00:00:00",
            reason="Test reason"
        )

        assert result == {
            "expired": True,
            "domain": "example.com",
            "transaction_id": "test-transaction",
            "bucket_name": "test-bucket",
            "certificate_arn": "test-arn",
            "expiration_date": "2023-01-01T00:00:00",
            "reason": "Test reason"
        }


class TestLoggingConfiguration:
    """Test suite for logging configuration."""

    def test_logger_configured(self):
        """Test that logger is properly configured."""
        assert isinstance(index.logger, logging.Logger)

    def test_log_level_from_environment(self):
        """Test that log level is set from environment variable."""
        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
            # Re-import to trigger module-level configuration
            import importlib
            importlib.reload(index)
            assert index.logger.level == logging.DEBUG