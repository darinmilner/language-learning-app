import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from helpers import get_certificate_details, is_certificate_expired, create_response

class TestCheckCertificateHelpers:
    
    def test_get_certificate_details_found(self):
        """Test getting certificate details when certificate exists"""
        with patch('helpers.boto3.client') as mock_boto:
            mock_acm = MagicMock()
            mock_boto.return_value = mock_acm
            
            mock_acm.list_certificates.return_value = {
                'CertificateSummaryList': [
                    {
                        'CertificateArn': 'arn:aws:acm:us-east-1:123456789012:certificate/12345678',
                        'DomainName': 'example.com'
                    }
                ]
            }
            
            mock_acm.describe_certificate.return_value = {
                'Certificate': {
                    'NotAfter': '2023-01-01T00:00:00Z',
                    'Status': 'ISSUED'
                }
            }
            
            result = get_certificate_details('example.com')
            
            assert result is not None
            assert result['certificate_arn'] == 'arn:aws:acm:us-east-1:123456789012:certificate/12345678'
            assert result['detail']['Status'] == 'ISSUED'
    
    def test_get_certificate_details_not_found(self):
        """Test getting certificate details when certificate doesn't exist"""
        with patch('helpers.boto3.client') as mock_boto:
            mock_acm = MagicMock()
            mock_boto.return_value = mock_acm
            
            mock_acm.list_certificates.return_value = {
                'CertificateSummaryList': []
            }
            
            result = get_certificate_details('example.com')
            
            assert result is None
    
    def test_is_certificate_expired_expired(self):
        """Test certificate expiration check for expired certificate"""
        past_date = (datetime.utcnow() - timedelta(days=1)).isoformat()
        cert_detail = {'NotAfter': past_date}
        
        result = is_certificate_expired(cert_detail)
        
        assert result['is_expired'] is True
        assert result['is_expiring_soon'] is True
    
    def test_is_certificate_expired_valid(self):
        """Test certificate expiration check for valid certificate"""
        future_date = (datetime.utcnow() + timedelta(days=60)).isoformat()
        cert_detail = {'NotAfter': future_date}
        
        result = is_certificate_expired(cert_detail)
        
        assert result['is_expired'] is False
        assert result['is_expiring_soon'] is False
    
    def test_is_certificate_expired_expiring_soon(self):
        """Test certificate expiration check for certificate expiring soon"""
        future_date = (datetime.utcnow() + timedelta(days=15)).isoformat()
        cert_detail = {'NotAfter': future_date}
        
        result = is_certificate_expired(cert_detail)
        
        assert result['is_expired'] is False
        assert result['is_expiring_soon'] is True
    
    def test_create_response_full(self):
        """Test creating response with all parameters"""
        response = create_response(
            expired=True,
            domain='example.com',
            transaction_id='test-transaction',
            bucket_name='test-bucket',
            certificate_arn='test-arn',
            expiration_date='2023-01-01T00:00:00',
            reason='Test reason'
        )
        
        assert response['expired'] is True
        assert response['domain'] == 'example.com'
        assert response['transaction_id'] == 'test-transaction'
        assert response['bucket_name'] == 'test-bucket'
        assert response['certificate_arn'] == 'test-arn'
        assert response['expiration_date'] == '2023-01-01T00:00:00'
        assert response['reason'] == 'Test reason'
    
    def test_create_response_minimal(self):
        """Test creating response with minimal parameters"""
        response = create_response(
            expired=False,
            domain='example.com',
            transaction_id='test-transaction',
            bucket_name='test-bucket'
        )
        
        assert response['expired'] is False
        assert response['domain'] == 'example.com'
        assert response['transaction_id'] == 'test-transaction'
        assert response['bucket_name'] == 'test-bucket'
        assert 'certificate_arn' not in response
        assert 'expiration_date' not in response
        assert 'reason' not in response