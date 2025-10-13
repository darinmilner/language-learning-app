import pytest
import os
from unittest.mock import patch, MagicMock
from index import lambda_handler

class TestCheckCertificateLambda:
    
    @pytest.fixture
    def mock_env(self):
        with patch.dict(os.environ, {'S3_BUCKET': 'test-bucket'}):
            yield
    
    @pytest.fixture
    def mock_uuid(self):
        with patch('index.uuid.uuid4') as mock_uuid:
            mock_uuid.return_value = 'test-transaction-id'
            yield mock_uuid
    
    @pytest.fixture
    def mock_helpers(self):
        with patch('index.get_certificate_details') as mock_get_cert, \
             patch('index.is_certificate_expired') as mock_is_expired, \
             patch('index.store_check_metadata') as mock_store_meta, \
             patch('index.create_response') as mock_create_resp:
            yield {
                'get_certificate_details': mock_get_cert,
                'is_certificate_expired': mock_is_expired,
                'store_check_metadata': mock_store_meta,
                'create_response': mock_create_resp
            }
    
    def test_lambda_handler_missing_s3_bucket(self):
        """Test that lambda handler raises error when S3_BUCKET is missing"""
        with pytest.raises(ValueError, match="S3_BUCKET environment variable is required"):
            lambda_handler({'domain': 'example.com'}, {})
    
    def test_lambda_handler_expired_certificate(self, mock_env, mock_uuid, mock_helpers):
        """Test lambda handler with expired certificate"""
        # Setup mocks
        mock_helpers['get_certificate_details'].return_value = {
            'certificate_arn': 'arn:aws:acm:us-east-1:123456789012:certificate/12345678',
            'detail': {'Status': 'ISSUED'}
        }
        mock_helpers['is_certificate_expired'].return_value = {
            'is_expired': True,
            'is_expiring_soon': True,
            'expiration_date': '2023-01-01T00:00:00'
        }
        mock_helpers['create_response'].return_value = {
            'expired': True,
            'domain': 'example.com',
            'transaction_id': 'test-transaction-id',
            'bucket_name': 'test-bucket'
        }
        
        # Execute
        event = {'domain': 'example.com'}
        result = lambda_handler(event, {})
        
        # Assert
        mock_helpers['get_certificate_details'].assert_called_once_with('example.com')
        mock_helpers['is_certificate_expired'].assert_called_once()
        mock_helpers['store_check_metadata'].assert_called_once()
        mock_helpers['create_response'].assert_called_once_with(
            expired=True,
            domain='example.com',
            transaction_id='test-transaction-id',
            bucket_name='test-bucket',
            certificate_arn='arn:aws:acm:us-east-1:123456789012:certificate/12345678',
            expiration_date='2023-01-01T00:00:00',
            reason='Certificate expired or expiring soon'
        )
        assert result['expired'] is True
    
    def test_lambda_handler_no_certificate_found(self, mock_env, mock_uuid, mock_helpers):
        """Test lambda handler when no certificate is found"""
        # Setup mocks
        mock_helpers['get_certificate_details'].return_value = None
        mock_helpers['create_response'].return_value = {
            'expired': True,
            'domain': 'example.com',
            'transaction_id': 'test-transaction-id',
            'bucket_name': 'test-bucket',
            'reason': 'No certificate found in ACM'
        }
        
        # Execute
        event = {'domain': 'example.com'}
        result = lambda_handler(event, {})
        
        # Assert
        mock_helpers['get_certificate_details'].assert_called_once_with('example.com')
        mock_helpers['store_check_metadata'].assert_called_once_with(
            'test-bucket', 'test-transaction-id', 'example.com', None, {}
        )
        mock_helpers['create_response'].assert_called_once_with(
            expired=True,
            domain='example.com',
            transaction_id='test-transaction-id',
            bucket_name='test-bucket',
            reason='No certificate found in ACM'
        )
        assert result['expired'] is True
    
    def test_lambda_handler_exception(self, mock_env, mock_uuid, mock_helpers):
        """Test lambda handler when an exception occurs"""
        # Setup mocks
        mock_helpers['get_certificate_details'].side_effect = Exception("Test error")
        
        with patch('index.store_error_metadata') as mock_store_error:
            # Execute & Assert
            with pytest.raises(Exception, match="Test error"):
                lambda_handler({'domain': 'example.com'}, {})
            
            # Verify error metadata was stored
            mock_store_error.assert_called_once_with(
                'test-bucket', 'test-transaction-id', 'example.com', 'Test error'
            )