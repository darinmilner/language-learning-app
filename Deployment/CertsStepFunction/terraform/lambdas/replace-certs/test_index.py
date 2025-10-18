import os
from unittest.mock import Mock, patch

import pytest

import index


class TestReplaceCertificateLambda:
    """Test suite for replace certificate Lambda function."""

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
        return {
            "domain": "example.com",
            "transaction_id": "test-transaction",
            "certificate_arn": "old-cert-arn"
        }

    @pytest.fixture
    def mock_certificate_data(self):
        """Return mock certificate data."""
        return (
            "MOCK_CERTIFICATE",
            "MOCK_PRIVATE_KEY", 
            "MOCK_CHAIN",
            "2024-01-01T00:00:00"
        )

    def test_lambda_handler_missing_bucket_name(self, sample_event):
        """Test Lambda handler raises error when S3_BUCKET is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="S3_BUCKET environment variable is required"):
                index.lambda_handler(sample_event, {})

    def test_lambda_handler_success(
        self, setup_env, mock_aws_clients, sample_event, mock_certificate_data
    ):
        """Test successful certificate replacement."""
        with patch("index.retrieve_certificate_from_s3", return_value=mock_certificate_data), \
             patch("index.import_certificate_to_acm", return_value="new-cert-arn"), \
             patch("index.delete_old_certificate", return_value=(True, None)), \
             patch("index.update_certificate_inventories") as mock_update_inventory, \
             patch("index.store_replacement_artifacts") as mock_store_artifacts:

            result = index.lambda_handler(sample_event, {})

        assert result["success"] is True
        assert result["new_certificate_arn"] == "new-cert-arn"
        assert result["old_certificate_deleted"] is True
        mock_update_inventory.assert_called_once()
        mock_store_artifacts.assert_called_once()

    def test_lambda_handler_failure(
        self, setup_env, mock_aws_clients, sample_event
    ):
        """Test certificate replacement failure."""
        with patch("index.retrieve_certificate_from_s3") as mock_retrieve, \
             patch("index.store_replacement_error") as mock_store_error:

            mock_retrieve.side_effect = Exception("S3 error")

            result = index.lambda_handler(sample_event, {})

        assert result["success"] is False
        assert "S3 error" in result["error"]
        mock_store_error.assert_called_once()


class TestRetrieveCertificateFromS3:
    """Test suite for retrieve_certificate_from_s3 function."""

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

    def test_retrieve_certificate_from_s3_success(self, setup_env, mock_s3):
        """Test successful certificate retrieval from S3."""
        # Mock S3 responses
        mock_cert_response = Mock()
        mock_cert_response["Body"].read.return_value = b"MOCK_CERTIFICATE"
        mock_cert_response.get.return_value = {"expiration-date": "2024-01-01T00:00:00"}

        mock_key_response = Mock()
        mock_key_response["Body"].read.return_value = b"MOCK_PRIVATE_KEY"

        mock_chain_response = Mock()
        mock_chain_response["Body"].read.return_value = b"MOCK_CHAIN"

        mock_s3.get_object.side_effect = [mock_cert_response, mock_key_response, mock_chain_response]

        cert, key, chain, expiration = index.retrieve_certificate_from_s3("example.com")

        assert cert == "MOCK_CERTIFICATE"
        assert key == "MOCK_PRIVATE_KEY"
        assert chain == "MOCK_CHAIN"
        assert expiration == "2024-01-01T00:00:00"

        # Verify S3 calls
        assert mock_s3.get_object.call_count == 3
        calls = mock_s3.get_object.call_args_list
        assert "cert.pem" in calls[0][1]["Key"]
        assert "privkey.pem" in calls[1][1]["Key"]
        assert "chain.pem" in calls[2][1]["Key"]


class TestImportCertificateToAcm:
    """Test suite for import_certificate_to_acm function."""

    @pytest.fixture
    def mock_acm(self):
        """Mock ACM client."""
        with patch("index.acm") as mock_acm:
            yield mock_acm

    def test_import_certificate_to_acm_success(self, mock_acm):
        """Test successful certificate import to ACM."""
        mock_acm.import_certificate.return_value = {
            "CertificateArn": "arn:aws:acm:us-east-1:123456789012:certificate/new-cert"
        }

        result = index.import_certificate_to_acm("cert", "key", "chain")

        assert result == "arn:aws:acm:us-east-1:123456789012:certificate/new-cert"
        mock_acm.import_certificate.assert_called_once_with(
            Certificate="cert",
            PrivateKey="key", 
            CertificateChain="chain"
        )


class TestDeleteOldCertificate:
    """Test suite for delete_old_certificate function."""

    @pytest.fixture
    def mock_acm(self):
        """Mock ACM client."""
        with patch("index.acm") as mock_acm:
            yield