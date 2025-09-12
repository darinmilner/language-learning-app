import unittest
from unittest.mock import patch, MagicMock
import os
from index import lambda_handler

class TestReplaceCertificate(unittest.TestCase):
    
    @patch('index.boto3.client')
    @patch('index.os.environ', {'CERTIFICATE_BUCKET': 'test-bucket'})
    def test_successful_certificate_replacement(self, mock_boto):
        # Mock AWS clients
        mock_s3 = MagicMock()
        mock_acm = MagicMock()
        mock_boto.side_effect = [mock_s3, mock_acm]
        
        # Mock S3 get_object responses
        mock_s3.get_object.side_effect = [
            {'Body': MagicMock(read=MagicMock(return_value=b'cert content'))},
            {'Body': MagicMock(read=MagicMock(return_value=b'key content'))},
            {'Body': MagicMock(read=MagicMock(return_value=b'chain content'))}
        ]
        
        # Mock ACM import_certificate response
        mock_acm.import_certificate.return_value = {
            'CertificateArn': 'arn:aws:acm:us-east-1:123456789012:certificate/new-cert'
        }
        
        # Call lambda handler
        result = lambda_handler({
            'domain': 'example.com',
            'certificate_arn': 'arn:aws:acm:us-east-1:123456789012:certificate/old-cert'
        }, {})
        
        # Assert success
        self.assertTrue(result['success'])
        self.assertEqual(result['domain'], 'example.com')
        self.assertEqual(result['new_certificate_arn'], 'arn:aws:acm:us-east-1:123456789012:certificate/new-cert')
        
        # Verify ACM import_certificate was called
        mock_acm.import_certificate.assert_called_once()
    
    @patch('index.boto3.client')
    @patch('index.os.environ', {'CERTIFICATE_BUCKET': 'test-bucket'})
    def test_failed_certificate_replacement(self, mock_boto):
        # Mock AWS clients
        mock_s3 = MagicMock()
        mock_acm = MagicMock()
        mock_boto.side_effect = [mock_s3, mock_acm]
        
        # Mock S3 get_object to raise exception
        mock_s3.get_object.side_effect = Exception("S3 error")
        
        # Call lambda handler
        result = lambda_handler({
            'domain': 'example.com',
            'certificate_arn': 'arn:aws:acm:us-east-1:123456789012:certificate/old-cert'
        }, {})
        
        # Assert failure
        self.assertFalse(result['success'])
        self.assertEqual(result['domain'], 'example.com')