import json
import logging
import os
from datetime import datetime

import boto3

# Initialize AWS clients and environment variables
s3 = boto3.client("s3")
acm = boto3.client("acm")
bucket_name = os.environ.get("S3_BUCKET")
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()

# Configure logging
logger = logging.getLogger()
logger.setLevel(getattr(logging, log_level, logging.INFO))


def lambda_handler(event, context):
    """Lambda handler to replace certificates in ACM."""
    domain = event["domain"]
    transaction_id = event["transaction_id"]
    old_cert_arn = event.get("certificate_arn")

    logger.info("Starting certificate replacement for domain: %s", domain)
    logger.debug("Event: %s", event)

    if not bucket_name:
        logger.error("S3_BUCKET environment variable is required but not set")
        raise ValueError("S3_BUCKET environment variable is required")

    try:
        certificate, private_key, chain, expiration_date = retrieve_certificate_from_s3(domain)
        new_cert_arn = import_certificate_to_acm(certificate, private_key, chain)
        
        old_cert_deleted, deletion_error = delete_old_certificate(old_cert_arn)
        update_certificate_inventories(domain, old_cert_arn, new_cert_arn, expiration_date, transaction_id, old_cert_deleted)
        store_replacement_artifacts(transaction_id, domain, old_cert_arn, new_cert_arn, expiration_date)

        response = create_success_response(domain, transaction_id, new_cert_arn, old_cert_arn, expiration_date, old_cert_deleted, deletion_error)
        logger.info("Certificate replacement completed successfully: %s", response)
        return response

    except Exception as e:
        logger.error("Error during certificate replacement: %s", str(e), exc_info=True)
        store_replacement_error(transaction_id, domain, old_cert_arn, str(e))
        return create_error_response(domain, transaction_id, str(e))


def retrieve_certificate_from_s3(domain):
    """Retrieve certificate files from S3."""
    logger.info("Retrieving certificate from S3 for domain: %s", domain)

    cert_response = s3.get_object(Bucket=bucket_name, Key=f"certificates/{domain}/cert.pem")
    key_response = s3.get_object(Bucket=bucket_name, Key=f"certificates/{domain}/privkey.pem")
    chain_response = s3.get_object(Bucket=bucket_name, Key=f"certificates/{domain}/chain.pem")

    certificate = cert_response["Body"].read().decode("utf-8")
    private_key = key_response["Body"].read().decode("utf-8")
    chain = chain_response["Body"].read().decode("utf-8")

    cert_metadata = cert_response.get("Metadata", {})
    expiration_date = cert_metadata.get("expiration-date", "")

    logger.debug("Certificate files retrieved successfully from S3")
    return certificate, private_key, chain, expiration_date


def import_certificate_to_acm(certificate, private_key, chain):
    """Import certificate to AWS ACM."""
    logger.info("Importing certificate to ACM")

    response = acm.import_certificate(
        Certificate=certificate,
        PrivateKey=private_key,
        CertificateChain=chain
    )

    new_cert_arn = response["CertificateArn"]
    logger.info("Certificate imported to ACM: %s", new_cert_arn)
    return new_cert_arn


def delete_old_certificate(old_cert_arn):
    """Delete old certificate from ACM."""
    if not old_cert_arn:
        logger.debug("No old certificate ARN provided for deletion")
        return False, None

    logger.info("Attempting to delete old certificate: %s", old_cert_arn)

    try:
        acm.delete_certificate(CertificateArn=old_cert_arn)
        logger.info("Successfully deleted old certificate: %s", old_cert_arn)
        return True, None
    except Exception as e:
        logger.warning("Failed to delete old certificate %s: %s", old_cert_arn, str(e))
        return False, str(e)


def update_certificate_inventories(domain, old_cert_arn, new_cert_arn, expiration_date, transaction_id, old_cert_deleted):
    """Update certificate inventories in S3."""
    logger.info("Updating certificate inventories")

    # Update new certificate inventory
    update_certificate_inventory(domain, new_cert_arn, expiration_date, transaction_id, "active")

    # Update old certificate inventory if deleted
    if old_cert_deleted and old_cert_arn:
        logger.info("Updating inventory for deleted old certificate")
        update_certificate_inventory(domain, old_cert_arn, expiration_date, transaction_id, "deleted", new_cert_arn)


def update_certificate_inventory(domain, cert_arn, expiration_date, transaction_id, status, replaced_by=None):
    """Update individual certificate inventory in S3."""
    logger.debug("Updating certificate inventory for: %s", cert_arn)

    inventory = {
        "certificate_arn": cert_arn,
        "domain": domain,
        "expiration_date": expiration_date,
        "import_date": datetime.utcnow().isoformat() if status == "active" else None,
        "deletion_date": datetime.utcnow().isoformat() if status == "deleted" else None,
        "transaction_id": transaction_id,
        "status": status,
        "replaced_by": replaced_by
    }

    cert_id = cert_arn.split("/")[-1] if cert_arn else "unknown"
    key_suffix = "_deleted.json" if status == "deleted" else ".json"

    s3.put_object(
        Bucket=bucket_name,
        Key=f"inventory/certificates/{domain}_{cert_id}{key_suffix}",
        Body=json.dumps(inventory, indent=2, default=str),
        ServerSideEncryption="aws:kms"
    )
    logger.debug("Certificate inventory updated: inventory/certificates/%s_%s%s", domain, cert_id, key_suffix)


def store_replacement_artifacts(transaction_id, domain, old_cert_arn, new_cert_arn, expiration_date):
    """Store replacement artifacts in S3."""
    logger.info("Storing replacement artifacts in S3")

    store_replacement_metadata(transaction_id, domain, old_cert_arn, new_cert_arn, expiration_date)
    store_replacement_summary(transaction_id, domain, old_cert_arn, new_cert_arn, expiration_date)


def store_replacement_metadata(transaction_id, domain, old_cert_arn, new_cert_arn, expiration_date):
    """Store replacement metadata in S3."""
    logger.debug("Storing replacement metadata for transaction: %s", transaction_id)

    metadata = {
        "transaction_id": transaction_id,
        "domain": domain,
        "replacement_timestamp": datetime.utcnow().isoformat(),
        "old_certificate_arn": old_cert_arn,
        "new_certificate_arn": new_cert_arn,
        "expiration_date": expiration_date,
        "action": "certificate_replacement",
        "success": True
    }

    s3.put_object(
        Bucket=bucket_name,
        Key=f"transactions/{transaction_id}/replacementmetadata.json",
        Body=json.dumps(metadata, indent=2, default=str),
        ServerSideEncryption="aws:kms"
    )
    logger.info("Replacement metadata stored in S3: transactions/%s/replacementmetadata.json", transaction_id)


def store_replacement_summary(transaction_id, domain, old_cert_arn, new_cert_arn, expiration_date):
    """Store replacement summary in S3."""
    logger.debug("Storing replacement summary for transaction: %s", transaction_id)

    summary = {
        "transaction_id": transaction_id,
        "domain": domain,
        "import_timestamp": datetime.utcnow().isoformat(),
        "old_certificate_arn": old_cert_arn,
        "new_certificate_arn": new_cert_arn,
        "expiration_date": expiration_date,
        "s3_bucket": bucket_name,
        "s3_certificate_path": f"certificates/{domain}/",
        "s3_transaction_path": f"transactions/{transaction_id}/"
    }

    s3.put_object(
        Bucket=bucket_name,
        Key=f"summary/{domain}/replacement_{transaction_id}.json",
        Body=json.dumps(summary, indent=2, default=str),
        ServerSideEncryption="aws:kms"
    )
    logger.debug("Replacement summary stored in S3: summary/%s/replacement_%s.json", domain, transaction_id)


def store_replacement_error(transaction_id, domain, old_cert_arn, error_message):
    """Store replacement error metadata in S3."""
    logger.error("Storing replacement error metadata for transaction: %s", transaction_id)

    metadata = {
        "transaction_id": transaction_id,
        "domain": domain,
        "replacement_timestamp": datetime.utcnow().isoformat(),
        "old_certificate_arn": old_cert_arn,
        "action": "certificate_replacement",
        "success": False,
        "error": error_message
    }

    s3.put_object(
        Bucket=bucket_name,
        Key=f"transactions/{transaction_id}/replacementerror.json",
        Body=json.dumps(metadata, indent=2),
        ServerSideEncryption="aws:kms"
    )
    logger.info("Replacement error metadata stored in S3: transactions/%s/replacementerror.json", transaction_id)


def create_success_response(domain, transaction_id, new_cert_arn, old_cert_arn, expiration_date, old_cert_deleted, deletion_error):
    """Create success response for certificate replacement."""
    return {
        "success": True,
        "domain": domain,
        "new_certificate_arn": new_cert_arn,
        "old_certificate_arn": old_cert_arn,
        "transaction_id": transaction_id,
        "bucket_name": bucket_name,
        "expiration_date": expiration_date,
        "old_certificate_deleted": old_cert_deleted,
        "deletion_error": deletion_error
    }


def create_error_response(domain, transaction_id, error_message):
    """Create error response for certificate replacement failure."""
    return {
        "success": False,
        "error": error_message,
        "domain": domain,
        "transaction_id": transaction_id
    }