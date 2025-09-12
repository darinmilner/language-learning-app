import logging
import os
import boto3

logger = logging.getLogger()
logger.setLevel("INFO")

bucket_name = os.environ.get('CERTIFICATE_BUCKET')
s3 = boto3.client('s3')
acm = boto3.client('acm')

def lambda_handler(event, context):
    domain = event['domain']    
    old_cert_arn = event.get('certificate_arn')
    logger.info(f"Event {event}")
        
    try:
        # Retrieve certificate files from S3
        cert_response = s3.get_object(Bucket=bucket_name, Key=f"{domain}/cert.pem")
        key_response = s3.get_object(Bucket=bucket_name, Key=f"{domain}/privkey.pem")
        chain_response = s3.get_object(Bucket=bucket_name, Key=f"{domain}/chain.pem")
        
        certificate = cert_response['Body'].read().decode('utf-8')
        private_key = key_response['Body'].read().decode('utf-8')
        chain = chain_response['Body'].read().decode('utf-8')
        
        # Import certificate to ACM
        response = acm.import_certificate(
            Certificate=certificate,
            PrivateKey=private_key,
            CertificateChain=chain
        )
        
        new_cert_arn = response['CertificateArn']
        
        # Delete old certificate if it exists
        if old_cert_arn:
            try:
                acm.delete_certificate(CertificateArn=old_cert_arn)
            except Exception as e:
                # Log but don't fail if deletion fails
                logger.error(f"Failed to delete old certificate: {str(e)}")
        
        return {
            'success': True,
            'domain': domain,
            'new_certificate_arn': new_cert_arn,
            'old_certificate_arn': old_cert_arn
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'domain': domain
        }