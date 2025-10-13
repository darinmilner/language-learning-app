import boto3
import json
from datetime import datetime

s3 = boto3.client('s3')
acm = boto3.client('acm')

def retrieve_certificate_from_s3(bucket_name, domain):
    """Retrieve certificate files from S3"""
    cert_response = s3.get_object(Bucket=bucket_name, Key=f"certificates/{domain}/cert.pem")
    key_response = s3.get_object(Bucket=bucket_name, Key=f"certificates/{domain}/privkey.pem")
    chain_response = s3.get_object(Bucket=bucket_name, Key=f"certificates/{domain}/chain.pem")
    
    certificate = cert_response['Body'].read().decode('utf-8')
    private_key = key_response['Body'].read().decode('utf-8')
    chain = chain_response['Body'].read().decode('utf-8')
    
    # Get metadata from certificate file
    cert_metadata = cert_response.get('Metadata', {})
    expiration_date = cert_metadata.get('expiration-date', '')
    
    return certificate, private_key, chain, expiration_date

def import_certificate_to_acm(certificate, private_key, chain):
    """Import certificate to AWS ACM"""
    response = acm.import_certificate(
        Certificate=certificate,
        PrivateKey=private_key,
        CertificateChain=chain
    )
    
    return response['CertificateArn']

def delete_old_certificate(old_cert_arn):
    """Delete old certificate from ACM"""
    if not old_cert_arn:
        return False, None
    
    try:
        acm.delete_certificate(CertificateArn=old_cert_arn)
        return True, None
    except Exception as e:
        return False, str(e)

def store_replacement_metadata(bucket_name, transaction_id, domain, old_cert_arn, new_cert_arn, expiration_date, success=True, error=None):
    """Store certificate replacement metadata in S3"""
    metadata = {
        'transaction_id': transaction_id,
        'domain': domain,
        'replacement_timestamp': datetime.utcnow().isoformat(),
        'old_certificate_arn': old_cert_arn,
        'new_certificate_arn': new_cert_arn,
        'expiration_date': expiration_date,
        'action': 'certificate_replacement',
        'success': success
    }
    
    if error:
        metadata['error'] = error
    
    key = "replacement_metadata.json" if success else "replacement_error.json"
    
    s3.put_object(
        Bucket=bucket_name,
        Key=f"transactions/{transaction_id}/{key}",
        Body=json.dumps(metadata, indent=2, default=str),
        ServerSideEncryption='aws:kms'
    )

def store_replacement_summary(bucket_name, transaction_id, domain, old_cert_arn, new_cert_arn, expiration_date):
    """Store replacement summary for easy querying"""
    summary = {
        'transaction_id': transaction_id,
        'domain': domain,
        'import_timestamp': datetime.utcnow().isoformat(),
        'old_certificate_arn': old_cert_arn,
        'new_certificate_arn': new_cert_arn,
        'expiration_date': expiration_date,
        's3_bucket': bucket_name,
        's3_certificate_path': f"certificates/{domain}/",
        's3_transaction_path': f"transactions/{transaction_id}/"
    }
    
    s3.put_object(
        Bucket=bucket_name,
        Key=f"summary/{domain}/replacement_{transaction_id}.json",
        Body=json.dumps(summary, indent=2, default=str),
        ServerSideEncryption='aws:kms'
    )

def update_certificate_inventory(bucket_name, domain, cert_arn, expiration_date, transaction_id, status='active', replaced_by=None):
    """Update certificate inventory in S3"""
    inventory = {
        'certificate_arn': cert_arn,
        'domain': domain,
        'expiration_date': expiration_date,
        'import_date': datetime.utcnow().isoformat() if status == 'active' else None,
        'deletion_date': datetime.utcnow().isoformat() if status == 'deleted' else None,
        'transaction_id': transaction_id,
        'status': status,
        'replaced_by': replaced_by
    }
    
    cert_id = cert_arn.split('/')[-1] if cert_arn else 'unknown'
    key_suffix = '_deleted.json' if status == 'deleted' else '.json'
    
    s3.put_object(
        Bucket=bucket_name,
        Key=f"inventory/certificates/{domain}_{cert_id}{key_suffix}",
        Body=json.dumps(inventory, indent=2, default=str),
        ServerSideEncryption='aws:kms'
    )