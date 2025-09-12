import sys
import unittest
from unittest.mock import patch, MagicMock
import os
from ..check_certificate import lambda_handler

# Add layer path to sys.path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../layers/python'))

class TestCheckCertificate(unittest.TestCase):
    
    @patch('index.boto3.client')
    @patch('index.os.environ', {'CERTIFICATE_BUCKET': 'test-bucket'})
    def test_expired_certificate(self, mock_boto):
        # Mock AWS clients
        mock_acm = MagicMock()
        mock_s3 = MagicMock()
        mock_boto.side_effect = [mock_acm, mock_s3]
        
        # Mock certificate data
        mock_acm.list_certificates.return_value = {
            'CertificateSummaryList': [
                {
                    'CertificateArn': 'arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012',
                    'DomainName': 'example.com'
                }
            ]
        }
        
        mock_acm.describe_certificate.return_value = {
            'Certificate': {
                'NotAfter': '2023-01-01T00:00:00Z'  # Past date
            }
        }
        
        # Mock S3 head_object to simulate certificate exists
        mock_s3.head_object.return_value = True
        
        # Call lambda handler
        result = lambda_handler({'domain': 'example.com'}, {})
        
        # Assert certificate is expired
        self.assertTrue(result['expired'])
        self.assertEqual(result['domain'], 'example.com')
    
    @patch('index.boto3.client')
    @patch('index.os.environ', {'CERTIFICATE_BUCKET': 'test-bucket'})
    def test_certificate_in_s3_not_acm(self, mock_boto):
        # Mock AWS clients
        mock_acm = MagicMock()
        mock_s3 = MagicMock()
        mock_boto.side_effect = [mock_acm, mock_s3]
        
        # Mock no certificates in ACM
        mock_acm.list_certificates.return_value = {
            'CertificateSummaryList': []
        }
        
        # Mock S3 head_object to simulate certificate exists
        mock_s3.head_object.return_value = True
        
        # Call lambda handler
        result = lambda_handler({'domain': 'example.com'}, {})
        
        # Assert certificate is marked as expired (to trigger import)
        self.assertTrue(result['expired'])
        self.assertIsNone(result['certificate_arn'])
    
    @patch('index.boto3.client')
    @patch('index.os.environ', {'CERTIFICATE_BUCKET': 'test-bucket'})
    def test_no_certificate_anywhere(self, mock_boto):
        # Mock AWS clients
        mock_acm = MagicMock()
        mock_s3 = MagicMock()
        mock_boto.side_effect = [mock_acm, mock_s3]
        
        # Mock no certificates in ACM
        mock_acm.list_certificates.return_value = {
            'CertificateSummaryList': []
        }
        
        # Mock S3 head_object to simulate certificate doesn't exist
        mock_s3.head_object.side_effect = Exception("Not found")
        
        # Call lambda handler
        result = lambda_handler({'domain': 'example.com'}, {})
        
        # Assert certificate is marked as expired (to trigger generation)
        self.assertTrue(result['expired'])
        self.assertIsNone(result['certificate_arn'])