import os
import logging
from helpers import (
    retrieve_certificate_from_s3, 
    import_certificate_to_acm, 
    delete_old_certificate,
    store_replacement_metadata,
    store_replacement_summary,
    update_certificate_inventory
)

bucket_name = os.environ.get("S3_BUCKET")
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()

logger = logging.getLogger()
logger.setLevel(getattr(logging, log_level, logging.INFO))

def lambda_handler(event, context):
    domain = event['domain']
    transaction_id = event['transaction_id']
    old_cert_arn = event.get('certificate_arn')
    
    if not bucket_name:
        logger.error("S3_BUCKET environment variable is required but not set")
        raise ValueError("S3_BUCKET environment variable is required")
    try:
        # Retrieve certificate from S3
        certificate, private_key, chain, expiration_date = retrieve_certificate_from_s3(bucket_name, domain)
        
        # Import certificate to ACM
        new_cert_arn = import_certificate_to_acm(certificate, private_key, chain)
        
        # Delete old certificate if it exists
        old_cert_deleted, deletion_error = delete_old_certificate(old_cert_arn)
        
        # Store replacement metadata
        store_replacement_metadata(
            bucket_name, 
            transaction_id, 
            domain, 
            old_cert_arn, 
            new_cert_arn, 
            expiration_date, 
            success=True
        )
        
        # Store replacement summary
        store_replacement_summary(
            bucket_name, 
            transaction_id, 
            domain, 
            old_cert_arn, 
            new_cert_arn, 
            expiration_date
        )
        
        # Update certificate inventory
        update_certificate_inventory(
            bucket_name, 
            domain, 
            new_cert_arn, 
            expiration_date, 
            transaction_id, 
            status='active'
        )
        
        # If old certificate was deleted, update its inventory
        if old_cert_deleted and old_cert_arn:
            update_certificate_inventory(
                bucket_name, 
                domain, 
                old_cert_arn, 
                expiration_date, 
                transaction_id, 
                status='deleted', 
                replaced_by=new_cert_arn
            )
        
        return {
            'success': True,
            'domain': domain,
            'new_certificate_arn': new_cert_arn,
            'old_certificate_arn': old_cert_arn,
            'transaction_id': transaction_id,
            'bucket_name': bucket_name,
            'expiration_date': expiration_date,
            'old_certificate_deleted': old_cert_deleted,
            'deletion_error': deletion_error
        }
        
    except Exception as e:
        # Store error metadata
        store_replacement_metadata(
            bucket_name, 
            transaction_id, 
            domain, 
            old_cert_arn, 
            None, 
            None, 
            success=False, 
            error=str(e)
        )
        
        return {
            'success': False,
            'error': str(e),
            'domain': domain,
            'transaction_id': transaction_id
        }