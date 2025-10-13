import uuid
import os 
import json
import logging 
import boto3
from helpers import get_certificate_details, is_certificate_expired, store_check_metadata, create_response
from datetime import datetime
    
s3 = boto3.client('s3')
bucket_name = os.environ.get("S3_BUCKET")
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()

logger = logging.getLogger()
logger.setLevel(getattr(logging, log_level, logging.INFO))

def lambda_handler(event, context):
    domain = event.get('domain', 'example.com')
    transaction_id = str(uuid.uuid4())
    
    logger.info(f"Starting certificate check for domain: {domain}")
    logger.debug(f"Event: {event}")
    
    if not bucket_name:
        logger.error("S3_BUCKET environment variable is required but not set")
        raise ValueError("S3_BUCKET environment variable is required")
    
    try:
        # Get certificate details from ACM
        certificate_data = get_certificate_details(domain)
        
        if certificate_data:
            # Check certificate expiration
            logger.info(f"Found certificate: {certificate_data['certificate_arn']}")
            check_result = is_certificate_expired(certificate_data['detail'])
            
            # Store metadata in S3
            store_check_metadata(bucket_name, transaction_id, domain, certificate_data, check_result)
            
            if check_result['is_expired'] or check_result['is_expiring_soon']:
                logger.warning(f"Certificate is expired or expiring soon: {check_result}")
                resp = create_response(
                    expired=True,
                    domain=domain,
                    transaction_id=transaction_id,
                    bucket_name=bucket_name,
                    certificate_arn=certificate_data['certificate_arn'],
                    expiration_date=check_result['expiration_date'],
                    reason='Certificate expired or expiring soon'
                )
                logger.info(f"Certificate check completed - expired: {resp}")
                return resp 
            else:
                logger.info("Certificate is valid and not expiring soon")
                return create_response(
                    expired=False,
                    domain=domain,
                    transaction_id=transaction_id,
                    bucket_name=bucket_name,
                    certificate_arn=certificate_data['certificate_arn'],
                    expiration_date=check_result['expiration_date']
                )
        else:
            # No certificate found
            logger.warning(f"No certificate found in ACM for domain: {domain}")
            store_check_metadata(bucket_name, transaction_id, domain, None, {})
            
            return create_response(
                expired=True,
                domain=domain,
                transaction_id=transaction_id,
                bucket_name=bucket_name,
                reason='No certificate found in ACM'
            )
            
    except Exception as e:
        # Store error metadata
        logger.error(f"Error during certificate check: {str(e)}", exc_info=True)
        store_error_metadata(transaction_id, domain, str(e))
        raise e

def store_error_metadata(transaction_id, domain, error_message):
    """Store error metadata in S3"""
    
    error_metadata = {
        'transaction_id': transaction_id,
        'domain': domain,
        'error_timestamp': datetime.utcnow().isoformat(),
        'error_message': error_message,
        'action': 'certificate_check_error'
    }
    
    s3.put_object(
        Bucket=bucket_name,
        Key=f"transactions/{transaction_id}/error_metadata.json",
        Body=json.dumps(error_metadata, indent=2),
        ServerSideEncryption='aws:kms'
    )