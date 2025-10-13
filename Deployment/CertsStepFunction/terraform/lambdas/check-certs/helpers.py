import boto3
from datetime import datetime, timedelta
import json

acm = boto3.client('acm')
s3 = boto3.client('s3')

def get_certificate_details(domain):
    """Get certificate details from ACM for a specific domain"""
    certificates = acm.list_certificates()['CertificateSummaryList']
    for cert in certificates:
        if cert['DomainName'] == domain:
            cert_detail = acm.describe_certificate(CertificateArn=cert['CertificateArn'])
            return {
                'certificate_arn': cert['CertificateArn'],
                'detail': cert_detail['Certificate']
            }
    return None

def is_certificate_expired(certificate_detail):
    """Check if certificate is expired or expiring soon"""
    expiration = certificate_detail['NotAfter']
    expiration_date = expiration.replace(tzinfo=None)
    
    is_expired = expiration_date < datetime.utcnow()
    is_expiring_soon = expiration_date < (datetime.utcnow() + timedelta(days=30))
    
    return {
        'is_expired': is_expired,
        'is_expiring_soon': is_expiring_soon,
        'expiration_date': expiration_date.isoformat()
    }

def store_check_metadata(bucket_name, transaction_id, domain, certificate_data, check_result):
    """Store certificate check metadata in S3"""
    metadata = {
        'transaction_id': transaction_id,
        'domain': domain,
        'check_timestamp': datetime.utcnow().isoformat(),
        'action': 'certificate_check',
        'certificate_arn': certificate_data.get('certificate_arn') if certificate_data else None,
        'certificate_status': certificate_data['detail']['Status'] if certificate_data else 'NOT_FOUND',
        'expiration_date': check_result.get('expiration_date'),
        'is_expired': check_result.get('is_expired'),
        'is_expiring_soon': check_result.get('is_expiring_soon')
    }
    
    s3.put_object(
        Bucket=bucket_name,
        Key=f"transactions/{transaction_id}/check_metadata.json",
        Body=json.dumps(metadata, indent=2, default=str),
        ServerSideEncryption='aws:kms'
    )
    
    return metadata

def create_response(expired, domain, transaction_id, bucket_name, certificate_arn=None, expiration_date=None, reason=None):
    """Create standardized Lambda response"""
    response = {
        'expired': expired,
        'domain': domain,
        'transaction_id': transaction_id,
        'bucket_name': bucket_name
    }
    
    if certificate_arn:
        response['certificate_arn'] = certificate_arn
    if expiration_date:
        response['expiration_date'] = expiration_date
    if reason:
        response['reason'] = reason
        
    return response