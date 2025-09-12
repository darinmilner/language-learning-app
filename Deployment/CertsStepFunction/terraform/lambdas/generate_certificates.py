import os
import boto3
import subprocess
import tempfile
import logging

logger = logging.getLogger()
logger.setLevel("INFO")
bucket_name = os.environ.get('CERTIFICATE_BUCKET')

def lambda_handler(event, context):
    domain = event['domain']
    logger.info(f"Event {event}")
    
    # Create temporary directory for Certbot
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # Generate certificate using Certbot
            subprocess.run([
                'certbot', 'certonly',
                '--dns-route53',
                '--domains', domain,
                '--non-interactive',
                '--agree-tos',
                '--config-dir', temp_dir,
                '--work-dir', '/tmp',
                '--logs-dir', '/tmp',
                '--email', 'admin@example.com'  # Should be parameterized
            ], check=True, capture_output=True, text=True)
            
            # Read certificate files
            cert_path = f"{temp_dir}/live/{domain}/cert.pem"
            key_path = f"{temp_dir}/live/{domain}/privkey.pem"
            chain_path = f"{temp_dir}/live/{domain}/chain.pem"
            
            with open(cert_path, 'r') as f:
                certificate = f.read()
            
            with open(key_path, 'r') as f:
                private_key = f.read()
            
            with open(chain_path, 'r') as f:
                chain = f.read()
            
            # Upload to S3
            s3 = boto3.client('s3')
            s3.put_object(
                Bucket=bucket_name,
                Key=f"{domain}/cert.pem",
                Body=certificate,
                ServerSideEncryption='AES256'
            )
            
            s3.put_object(
                Bucket=bucket_name,
                Key=f"{domain}/privkey.pem",
                Body=private_key,
                ServerSideEncryption='AES256'
            )
            
            s3.put_object(
                Bucket=bucket_name,
                Key=f"{domain}/chain.pem",
                Body=chain,
                ServerSideEncryption='AES256'
            )
            
            logger.info(f"Cert files uploaded to {bucket_name}")
            
            return {
                'success': True,
                'domain': domain,
                's3_location': f"s3://{bucket_name}/{domain}/"
            }
            
        except subprocess.CalledProcessError as e:
            return {
                'success': False,
                'error': f"Certificate generation failed: {e.stderr}",
                'domain': domain
            }