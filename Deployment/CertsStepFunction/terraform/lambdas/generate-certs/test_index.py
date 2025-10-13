import pytest
import os
from unittest.mock import patch, MagicMock
from index import lambda_handler

class TestGenerateCertificateLambda:
    
    @pytest.fixture
    def mock_env(self):
        with patch.dict(os.environ, {
            'S3_BUCKET': 'test-bucket',
            'CERTBOT_EMAIL': 'test@example.com'
        }):
            yield
    
    @pytest.fixture
    def mock_helpers(self):
        with patch('index.run_certbot_command') as mock_run_certbot, \
             patch('index.read_certificate_files') as mock_read_files, \
             patch('index.get_certificate_expiration') as mock_get_expiration, \
             patch('index.upload_certificate_to_s3') as mock_upload_s3, \
             patch('index.store_generation_metadata') as mock_store_meta:
            yield {
                'run_certbot_command': mock_run_certbot,
                'read_certificate_files': mock_read_files,
                'get_certificate_expiration': mock_get_expiration,
                'upload_certificate_to_s3': mock_upload_s3,
                'store_generation_metadata': mock_store_meta
            }
    
    def test_lambda_handler_success(self, mock_env, mock_helpers):
        """Test successful certificate generation"""
        # Setup mocks
        mock_helpers['run_certbot_command'].return_value = None
        mock_helpers['read_certificate_files'].return_value = (
            'cert-content', 'key-content', 'chain-content'
        )
        mock_helpers['get_certificate_expiration'].return_value = '2024-01-01T00:00:00'
        
        # Execute
        event = {
            'domain': 'example.com',
            'transaction_id': 'test-transaction',
            'certificate_arn': 'old-cert-arn'
        }
        result = lambda_handler(event, {})
        
        # Assert
        mock_helpers['run_certbot_command'].assert_called_once_with(
            'example.com', MagicMock(), 'test@example.com'
        )
        mock_helpers['upload_certificate_to_s3'].assert_called_once_with(
            'test-bucket', 'example.com', 'cert-content', 'key-content', 
            'chain-content', 'test-transaction', '2024-01-01T00:00:00'
        )
        mock_helpers['store_generation_metadata'].assert_called_once_with(
            'test-bucket', 'test-transaction', 'example.com', 'old-cert-arn',
            '2024-01-01T00:00:00', success=True
        )
        assert result['success'] is True
        assert result['domain'] == 'example.com'
    
    def test_lambda_handler_missing_s3_bucket(self):
        """Test that lambda handler raises error when S3_BUCKET is missing"""
        with pytest.raises(ValueError, match="S3_BUCKET environment variable is required"):
            lambda_handler({
                'domain': 'example.com',
                'transaction_id': 'test-transaction'
            }, {})