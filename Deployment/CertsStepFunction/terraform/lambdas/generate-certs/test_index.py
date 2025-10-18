import json
import os
import subprocess
import tempfile
from unittest.mock import Mock, patch

import pytest

import index


class TestGenerateCertificateLambda:
    """Test suite for generate certificate Lambda function."""

    @pytest.fixture
    def setup_env(self):
        """Set up environment variables for testing."""
        with patch.dict(os.environ, {
            "S3_BUCKET": "test-bucket",
            "CERTBOT_EMAIL": "test@example.com",
            "LOG_LEVEL": "INFO"
        }):
            yield

    @pytest.fixture
    def mock_aws_clients(self):
        """Mock AWS clients."""
        with patch("index.s3") as mock_s3:
            yield {"s3": mock_s3}

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
            "-----BEGIN CERTIFICATE-----\\nMOCK_CERT\\n-----END CERTIFICATE-----",
            "-----BEGIN PRIVATE KEY-----\\nMOCK_KEY\\n-----END PRIVATE KEY-----",
            "-----BEGIN CHAIN-----\\nMOCK_CHAIN\\n-----END CHAIN-----"
        )

    def test_lambda_handler_missing_bucket_name(self, sample_event):
        """Test Lambda handler raises error when S3_BUCKET is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="S3_BUCKET environment variable is required"):
                index.lambda_handler(sample_event, {})

    def test_lambda_handler_success(
        self, setup_env, mock_aws_clients, sample_event, mock_certificate_data
    ):
        """Test successful certificate generation."""
        with patch("index.run_certbot_command") as mock_certbot, \
             patch("index.read_certificate_files", return_value=mock_certificate_data), \
             patch("index.get_certificate_expiration", return_value="2024-01-01T00:00:00"), \
             patch("index.upload_certificate_to_s3") as mock_upload, \
             patch("index.store_generation_metadata") as mock_store_metadata:

            result = index.lambda_handler(sample_event, {})

        assert result["success"] is True
        assert result["domain"] == "example.com"
        assert result["transaction_id"] == "test-transaction"
        mock_certbot.assert_called_once()
        mock_upload.assert_called_once()
        mock_store_metadata.assert_called_once()

    def test_lambda_handler_certbot_failure(
        self, setup_env, mock_aws_clients, sample_event
    ):
        """Test certificate generation when Certbot fails."""
        with patch("index.run_certbot_command") as mock_certbot, \
             patch("index.store_generation_error") as mock_store_error:

            mock_certbot.side_effect = subprocess.CalledProcessError(
                1, "certbot", stderr="DNS validation failed"
            )

            result = index.lambda_handler(sample_event, {})

        assert result["success"] is False
        assert "DNS validation failed" in result["error"]
        mock_store_error.assert_called_once()

    def test_lambda_handler_unexpected_error(
        self, setup_env, mock_aws_clients, sample_event
    ):
        """Test certificate generation when unexpected error occurs."""
        with patch("index.run_certbot_command") as mock_certbot, \
             patch("index.store_generation_error") as mock_store_error:

            mock_certbot.side_effect = Exception("Unexpected error")

            with pytest.raises(Exception, match="Unexpected error"):
                index.lambda_handler(sample_event, {})

            mock_store_error.assert_called_once()


class TestRunCertbotCommand:
    """Test suite for run_certbot_command function."""

    @pytest.fixture
    def setup_env(self):
        """Set up environment variables."""
        with patch.dict(os.environ, {"CERTBOT_EMAIL": "test@example.com"}):
            yield

    def test_run_certbot_command_success(self, setup_env):
        """Test successful Certbot command execution."""
        with patch("subprocess.run") as mock_subprocess:
            mock_subprocess.return_value.returncode = 0
            result = index.run_certbot_command("example.com", "/tmp/certbot")

        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        assert "certbot" in call_args
        assert "example.com" in call_args
        assert "--dns-route53" in call_args

    def test_run_certbot_command_failure(self, setup_env):
        """Test Certbot command failure."""
        with patch("subprocess.run") as mock_subprocess:
            mock_subprocess.side_effect = subprocess.CalledProcessError(
                1, "certbot", stderr="Validation failed"
            )

            with pytest.raises(subprocess.CalledProcessError):
                index.run_certbot_command("example.com", "/tmp/certbot")


class TestReadCertificateFiles:
    """Test suite for read_certificate_files function."""

    def test_read_certificate_files_success(self):
        """Test successful reading of certificate files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create certificate directory structure
            cert_dir = f"{temp_dir}/live/example.com"
            os.makedirs(cert_dir, exist_ok=True)

            # Create mock certificate files
            with open(f"{cert_dir}/cert.pem", "w") as f:
                f.write("MOCK_CERTIFICATE")
            with open(f"{cert_dir}/privkey.pem", "w") as f:
                f.write("MOCK_PRIVATE_KEY")
            with open(f"{cert_dir}/chain.pem", "w") as f:
                f.write("MOCK_CHAIN")

            cert, key, chain = index.read_certificate_files("example.com", temp_dir)

            assert cert == "MOCK_CERTIFICATE"
            assert key == "MOCK_PRIVATE_KEY"
            assert chain == "MOCK_CHAIN"

    def test_read_certificate_files_missing(self):
        """Test reading certificate files when they don't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(FileNotFoundError):
                index.read_certificate_files("example.com", temp_dir)


class TestGetCertificateExpiration:
    """Test suite for get_certificate_expiration function."""

    def test_get_certificate_expiration_success(self):
        """Test successful certificate expiration extraction."""
        mock_certificate = """
-----BEGIN CERTIFICATE-----
MIIESTCCAzGgAwIBAgITB...MOCK_CERTIFICATE_CONTENT...
-----END CERTIFICATE-----
        """.strip()

        with patch("index.x509.load_pem_x509_certificate") as mock_load_cert:
            mock_cert = Mock()
            mock_cert.not_valid_after.isoformat.return_value = "2024-12-31T23:59:59"
            mock_load_cert.return_value = mock_cert

            expiration = index.get_certificate_expiration(mock_certificate)

        assert expiration == "2024-12-31T23:59:59"
        mock_load_cert.assert_called_once()


class TestUploadCertificateToS3:
    """Test suite for upload_certificate_to_s3 function."""

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

    def test_upload_certificate_to_s3_success(self, setup_env, mock_s3):
        """Test successful certificate upload to S3."""
        certificate = "MOCK_CERT"
        private_key = "MOCK_KEY"
        chain = "MOCK_CHAIN"

        index.upload_certificate_to_s3(
            "example.com", certificate, private_key, chain, "test-transaction", "2024-01-01T00:00:00"
        )

        # Should upload 3 files
        assert mock_s3.put_object.call_count == 3

        # Verify certificate upload
        cert_call = mock_s3.put_object.call_args_list[0]
        assert "cert.pem" in cert_call[1]["Key"]
        assert cert_call[1]["Body"] == "MOCK_CERT"

        # Verify private key upload
        key_call = mock_s3.put_object.call_args_list[1]
        assert "privkey.pem" in key_call[1]["Key"]
        assert key_call[1]["Body"] == "MOCK_KEY"

        # Verify chain upload
        chain_call = mock_s3.put_object.call_args_list[2]
        assert "chain.pem" in chain_call[1]["Key"]
        assert chain_call[1]["Body"] == "MOCK_CHAIN"


class TestStoreGenerationMetadata:
    """Test suite for store_generation_metadata function."""

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

    def test_store_generation_metadata_success(self, setup_env, mock_s3):
        """Test successful generation metadata storage."""
        index.store_generation_metadata(
            "test-transaction", "example.com", "old-cert-arn", "2024-01-01T00:00:00"
        )

        mock_s3.put_object.assert_called_once()
        call_args = mock_s3.put_object.call_args
        assert call_args[1]["Bucket"] == "test-bucket"
        assert "generation_metadata.json" in call_args[1]["Key"]

        body = json.loads(call_args[1]["Body"])
        assert body["success"] is True
        assert body["domain"] == "example.com"
        assert body["expiration_date"] == "2024-01-01T00:00:00"


class TestStoreGenerationError:
    """Test suite for store_generation_error function."""

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

    def test_store_generation_error_success(self, setup_env, mock_s3):
        """Test successful generation error storage."""
        index.store_generation_error(
            "test-transaction", "example.com", "old-cert-arn", "DNS validation failed"
        )

        mock_s3.put_object.assert_called_once()
        call_args = mock_s3.put_object.call_args
        assert call_args[1]["Bucket"] == "test-bucket"
        assert "generation_error.json" in call_args[1]["Key"]

        body = json.loads(call_args[1]["Body"])
        assert body["success"] is False
        assert body["error"] == "DNS validation failed"


class TestCreateErrorResponse:
    """Test suite for create_error_response function."""

    def test_create_error_response(self):
        """Test error response creation."""
        result = index.create_error_response("example.com", "test-transaction", "DNS failed")

        assert result == {
            "success": False,
            "error": "Certificate generation failed: DNS failed",
            "domain": "example.com",
            "transaction_id": "test-transaction"
        }