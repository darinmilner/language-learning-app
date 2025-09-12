import boto3
import logging
import os
from datetime import datetime, timedelta

bucket_name = os.environ.get('CERTIFICATE_BUCKET')
acm = boto3.client('acm')
s3 = boto3.client('s3')

logger = logging.getLogger()
logger.setLevel("INFO")

def lambda_handler(event, context):
    # Get domain from event or use default
    domain = event.get('domain', 'example.com')
    logger.info(f"Event {event}")
    # Check if certificate exists in S3 (previously generated)
    try:
        s3.head_object(Bucket=bucket_name, Key=f"{domain}/cert.pem")
        s3_cert_exists = True
    except Exception as e:
        s3_cert_exists = False
        logger.info("Certificate does not exist in S3")
    
    # Check ACM for existing certificate
    certificates = acm.list_certificates()['CertificateSummaryList']
    domain_cert = None
    
    for cert in certificates:
        if cert['DomainName'] == domain:
            domain_cert = cert
            break
    
    # If no certificate in ACM, check if we have one in S3
    if not domain_cert:
        if s3_cert_exists:
            return {
                'expired': True,  # Treat as expired to trigger import
                'certificate_arn': None,
                'domain': domain,
                'reason': 'Certificate found in S3 but not in ACM'
            }
        else:
            return {
                'expired': True,  # No certificate exists
                'certificate_arn': None,
                'domain': domain,
                'reason': 'No certificate found in ACM or S3'
            }
    
    # Get certificate details
    cert_detail = acm.describe_certificate(CertificateArn=domain_cert['CertificateArn'])
    expiration = cert_detail['Certificate']['NotAfter']
    expiration_date = expiration.replace(tzinfo=None)
    
    # Check if certificate is expired or expiring soon (within 30 days)
    if expiration_date < datetime.utcnow() or expiration_date < (datetime.utcnow() + timedelta(days=30)):
        return {
            'expired': True,
            'certificate_arn': domain_cert['CertificateArn'],
            'domain': domain,
            'expiration_date': expiration_date.isoformat()
        }
    
    return {
        'expired': False,
        'certificate_arn': domain_cert['CertificateArn'],
        'domain': domain,
        'expiration_date': expiration_date.isoformat()
    }