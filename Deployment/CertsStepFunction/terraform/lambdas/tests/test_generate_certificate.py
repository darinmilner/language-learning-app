import unittest
from unittest.mock import patch, MagicMock
import os
from ..generate_certificates import lambda_handler

class TestGenerateCertificate(unittest.TestCase):
    
    @patch('index.subprocess.run')
    @patch('index.boto3.client')
    @patch('index.tempfile.TemporaryDirectory')
    @patch('index.os.environ', {'CERTIFICATE_BUCKET': 'test-bucket'})
    def test_successful_certificate_generation(self, mock_tempdir, mock_boto, mock_subprocess):
        # Mock temporary directory
        mock_tempdir.return_value.__enter__.return_value = '/tmp/certbot'
        
        # Mock subprocess success
        mock_subprocess.return_value.returncode = 0
        
        # Mock S3 client
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        
        # Call lambda handler
        result = lambda_handler({'domain': 'example.com'}, {})
        
        # Assert success
        self.assertTrue(result['success'])
        self.assertEqual(result['domain'], 'example.com')
        
        # Verify S3 put_object was called 3 times (cert, key, chain)
        self.assertEqual(mock_s3.put_object.call_count, 3)
    
    @patch('index.subprocess.run')
    @patch('index.tempfile.TemporaryDirectory')
    @patch('index.os.environ', {'CERTIFICATE_BUCKET': 'test-bucket'})
    def test_failed_certificate_generation(self, mock_tempdir, mock_subprocess):
        # Mock temporary directory
        mock_tempdir.return_value.__enter__.return_value = '/tmp/certbot'
        
        # Mock subprocess failure
        mock_subprocess.side_effect = Exception("Certbot failed")
        
        # Call lambda handler
        result = lambda_handler({'domain': 'example.com'}, {})
        
        # Assert failure
        self.assertFalse(result['success'])
        self.assertEqual(result['domain'], 'example.com')