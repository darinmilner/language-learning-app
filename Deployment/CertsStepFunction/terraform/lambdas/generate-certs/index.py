import subprocess
import tempfile
import os
import logging
from helpers import run_certbot_command, read_certificate_files, get_certificate_expiration, upload_certificate_to_s3, store_generation_metadata

certbot_email = os.environ.get('CERTBOT_EMAIL', 'admin@example.com')
bucket_name = os.environ.get("S3_BUCKET")
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()

logger = logging.getLogger()
logger.setLevel(getattr(logging, log_level, logging.INFO))

def lambda_handler(event, context):
    domain = event['domain']
    transaction_id = event['transaction_id']
    old_cert_arn = event.get('certificate_arn')
    
    logger.info(f"Starting certificate generation for domain: {domain}")
    logger.debug(f"Event: {event}")
    
    if not bucket_name:
        logger.error("S3_BUCKET environment variable is required but not set")
        raise ValueError("S3_BUCKET environment variable is required")
   
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # Generate certificate using Certbot
            logger.info(f"Generating certificate using Certbot for domain: {domain}")
            run_certbot_command(domain, temp_dir, certbot_email)
            
            # Read generated certificate files
            logger.debug("Reading certificate files from filesystem")
            certificate, private_key, chain = read_certificate_files(domain, temp_dir)
            
            # Get certificate expiration date
            expiration_date = get_certificate_expiration(certificate)
            logger.info(f"Certificate expiration date: {expiration_date}")
            
            # Upload certificate files to S3
            logger.info("Uploading certificate files to S3")
            upload_certificate_to_s3(
                bucket_name, 
                domain, 
                certificate, 
                private_key, 
                chain, 
                transaction_id, 
                expiration_date
            )
            
            # Store generation metadata
            logger.info("Storing generation metadata in S3")
            store_generation_metadata(
                bucket_name, 
                transaction_id, 
                domain, 
                old_cert_arn, 
                expiration_date, 
                success=True
            )
            
            return {
                'success': True,
                'domain': domain,
                'transaction_id': transaction_id,
                'bucket_name': bucket_name,
                'expiration_date': expiration_date,
                's3_location': f"s3://{bucket_name}/certificates/{domain}/"
            }
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Certbot command failed: {e.stderr}")
            # Store error metadata
            store_generation_metadata(
                bucket_name, 
                transaction_id, 
                domain, 
                old_cert_arn, 
                None, 
                success=False, 
                error=e.stderr
            )
            
            return {
                'success': False,
                'error': f"Certificate generation failed: {e.stderr}",
                'domain': domain,
                'transaction_id': transaction_id
            }
        except Exception as e:
            logger.error(f"Unexpected error during certificate generation: {str(e)}", exc_info=True)
            # Store error metadata
            store_generation_metadata(
                bucket_name, 
                transaction_id, 
                domain, 
                old_cert_arn, 
                None, 
                success=False, 
                error=str(e)
            )
            
            raise e
