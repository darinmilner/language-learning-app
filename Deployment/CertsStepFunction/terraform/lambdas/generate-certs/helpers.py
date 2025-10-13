import subprocess
import boto3
import json
from datetime import datetime
from cryptography import x509
from cryptography.hazmat.backends import default_backend

s3 = boto3.client('s3')

def run_certbot_command(domain, temp_dir, email):
    """Run certbot command to generate certificate"""
    result = subprocess.run([
        'certbot', 'certonly',
        '--dns-route53',
        '--domains', domain,
        '--non-interactive',
        '--agree-tos',
        '--config-dir', temp_dir,
        '--work-dir', '/tmp',
        '--logs-dir', '/tmp',
        '--email', email
    ], check=True, capture_output=True, text=True)
    
    return result

def read_certificate_files(domain, temp_dir):
    """Read certificate files from filesystem"""
    cert_path = f"{temp_dir}/live/{domain}/cert.pem"
    key_path = f"{temp_dir}/live/{domain}/privkey.pem"
    chain_path = f"{temp_dir}/live/{domain}/chain.pem"
    
    with open(cert_path, 'r') as f:
        certificate = f.read()
    
    with open(key_path, 'r') as f:
        private_key = f.read()
    
    with open(chain_path, 'r') as f:
        chain = f.read()
    
    return certificate, private_key, chain

def get_certificate_expiration(certificate_content):
    """Extract expiration date from certificate"""
    cert_obj = x509.load_pem_x509_certificate(
        certificate_content.encode(), 
        default_backend()
    )
    return cert_obj.not_valid_after.isoformat()

def upload_certificate_to_s3(bucket_name, domain, certificate, private_key, chain, transaction_id, expiration_date):
    """Upload certificate files to S3 with metadata"""
    
    # Common metadata
    metadata = {
        'domain': domain,
        'expiration-date': expiration_date,
        'transaction-id': transaction_id,
        'generated-at': datetime.utcnow().isoformat()
    }
    
    # Upload certificate
    s3.put_object(
        Bucket=bucket_name,
        Key=f"certificates/{domain}/cert.pem",
        Body=certificate,
        ServerSideEncryption='aws:kms',
        Metadata=metadata
    )
    
    # Upload private key
    s3.put_object(
        Bucket=bucket_name,
        Key=f"certificates/{domain}/privkey.pem",
        Body=private_key,
        ServerSideEncryption='aws:kms',
        Metadata=metadata
    )
    
    # Upload chain
    s3.put_object(
        Bucket=bucket_name,
        Key=f"certificates/{domain}/chain.pem",
        Body=chain,
        ServerSideEncryption='aws:kms',
        Metadata=metadata
    )

def store_generation_metadata(bucket_name, transaction_id, domain, old_cert_arn, expiration_date, success=True, error=None):
    """Store certificate generation metadata in S3"""  
    metadata = {
        'transaction_id': transaction_id,
        'domain': domain,
        'generation_timestamp': datetime.utcnow().isoformat(),
        'old_certificate_arn': old_cert_arn,
        'action': 'certificate_generation',
        'success': success,
        'expiration_date': expiration_date if success else None
    }
    
    if error:
        metadata['error'] = error
    
    key = "generation_metadata.json" if success else "generation_error.json"
    
    s3.put_object(
        Bucket=bucket_name,
        Key=f"transactions/{transaction_id}/{key}",
        Body=json.dumps(metadata, indent=2, default=str),
        ServerSideEncryption='aws:kms'
    )