import pytest
import os
from unittest.mock import patch, MagicMock
from index import lambda_handler

class TestReplaceCertificateLambda:
    
    @pytest.fixture
    def mock_env(self):
        with patch.dict(os.environ, {'S3_BUCKET': 'test-bucket'}):
            yield
    
    @pytest.fixture
    def mock_helpers(self):
        with patch('index.retrieve_certificate_from_s3') as mock_retrieve, \
             patch('index.import_certificate_to_acm') as mock_import, \
             patch('index.delete_old_certificate') as mock_delete, \
             patch('index.store_replacement_metadata') as mock_store_meta, \
             patch('index.store_replacement_summary') as mock_store_summary, \
             patch('index.update_certificate_inventory') as mock_update_inv:
            yield {
                'retrieve_certificate_from_s3': mock_retrieve,
                'import_certificate_to_acm': mock_import,
                'delete_old_certificate': mock_delete,
                'store_replacement_metadata': mock_store_meta,
                'store_replacement_summary': mock_store_summary,
                'update_certificate_inventory': mock_update_inv
            }
    
    def test_lambda_handler_success(self, mock_env, mock_helpers):
        """Test successful certificate replacement"""
        # Setup mocks
        mock_helpers['retrieve_certificate_from_s3'].return_value = (
            'cert-content', 'key-content', 'chain-content', '2024-01-01T00:00:00'
        )
        mock_helpers['import_certificate_to_acm'].return_value = 'new-cert-arn'
        mock_helpers['delete_old_certificate'].return_value = (True, None)
        
        # Execute
        event = {
            'domain': 'example.com',
            'transaction_id': 'test-transaction',
            'certificate_arn': 'old-cert-arn'
        }
        result = lambda_handler(event, {})
        
        # Assert
        mock_helpers['retrieve_certificate_from_s3'].assert_called_once_with('test-bucket', 'example.com')
        mock_helpers['import_certificate_to_acm'].assert_called_once_with(
            'cert-content', 'key-content', 'chain-content'
        )
        mock_helpers['delete_old_certificate'].assert_called_once_with('old-cert-arn')
        mock_helpers['store_replacement_metadata'].assert_called_once_with(
            'test-bucket', 'test-transaction', 'example.com', 'old-cert-arn',
            'new-cert-arn', '2024-01-01T00:00:00', success=True
        )
        assert result['success'] is True
        assert result['new_certificate_arn'] == 'new-cert-arn'
    
    def test_lambda_handler_missing_s3_bucket(self):
        """Test that lambda handler raises error when S3_BUCKET is missing"""
        with pytest.raises(ValueError, match="S3_BUCKET environment variable is required"):
            lambda_handler({
                'domain': 'example.com',
                'transaction_id': 'test-transaction'
            }, {})