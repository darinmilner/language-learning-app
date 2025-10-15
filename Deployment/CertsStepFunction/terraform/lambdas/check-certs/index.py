import json
import logging
import os
import uuid
from datetime import datetime, timedelta

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
    """Lambda handler to check for expiring certificates."""
    domain = event.get("domain", "example.com")
    transaction_id = str(uuid.uuid4())

    logger.info("Starting certificate check for domain: %s", domain)
    logger.debug("Event: %s", event)

    if not bucket_name:
        logger.error("S3_BUCKET environment variable is required but not set")
        raise ValueError("S3_BUCKET environment variable is required")

    try:
        certificate_data = get_certificate_details(domain)

        if certificate_data:
            return handle_existing_certificate(certificate_data, domain, transaction_id)
        else:
            return handle_missing_certificate(domain, transaction_id)

    except Exception as e:
        logger.error("Error during certificate check: %s", str(e), exc_info=True)
        store_error_metadata(transaction_id, domain, str(e))
        raise e


def get_certificate_details(domain):
    """Get certificate details from ACM for a specific domain."""
    logger.debug("Searching ACM for certificate with domain: %s", domain)

    try:
        certificates = acm.list_certificates()["CertificateSummaryList"]
        logger.debug("Found %d certificates in ACM", len(certificates))

        for cert in certificates:
            if cert["DomainName"] == domain:
                logger.debug("Found matching certificate: %s", cert["CertificateArn"])
                cert_detail = acm.describe_certificate(CertificateArn=cert["CertificateArn"])
                return {
                    "certificate_arn": cert["CertificateArn"],
                    "detail": cert_detail["Certificate"],
                }

        logger.debug("No certificate found for domain: %s", domain)
        return None

    except Exception as e:
        logger.error("Error retrieving certificate details for domain %s: %s", domain, str(e))
        raise


def is_certificate_expired(certificate_detail):
    """Check if certificate is expired or expiring soon."""
    expiration = certificate_detail["NotAfter"]
    expiration_date = expiration.replace(tzinfo=None)
    current_time = datetime.utcnow()
    threshold_date = current_time + timedelta(days=30)

    is_expired = expiration_date < current_time
    is_expiring_soon = expiration_date < threshold_date

    logger.debug(
        "Certificate expiration: %s, Is expired: %s, Is expiring soon: %s",
        expiration_date,
        is_expired,
        is_expiring_soon,
    )

    return {
        "is_expired": is_expired,
        "is_expiring_soon": is_expiring_soon,
        "expiration_date": expiration_date.isoformat(),
    }


def store_check_metadata(transaction_id, domain, certificate_data, check_result):
    """Store certificate check metadata in S3."""
    logger.debug("Storing check metadata for transaction: %s", transaction_id)

    # Determine certificate status
    if certificate_data:
        certificate_arn = certificate_data.get("certificate_arn")
        certificate_status = certificate_data["detail"]["Status"]
    else:
        certificate_arn = None
        certificate_status = "NOT_FOUND"

    metadata = {
        "transaction_id": transaction_id,
        "domain": domain,
        "check_timestamp": datetime.utcnow().isoformat(),
        "action": "certificate_check",
        "certificate_arn": certificate_arn,
        "certificate_status": certificate_status,
        "expiration_date": check_result.get("expiration_date"),
        "is_expired": check_result.get("is_expired"),
        "is_expiring_soon": check_result.get("is_expiring_soon"),
    }

    s3.put_object(
        Bucket=bucket_name,
        Key=f"transactions/{transaction_id}/check_metadata.json",
        Body=json.dumps(metadata, indent=2, default=str),
        ServerSideEncryption="aws:kms",
    )
    logger.info("Check metadata stored in S3: transactions/%s/check_metadata.json", transaction_id)

    return metadata


def store_error_metadata(transaction_id, domain, error_message):
    """Store error metadata in S3."""
    logger.error("Storing error metadata for transaction: %s", transaction_id)

    error_metadata = {
        "transaction_id": transaction_id,
        "domain": domain,
        "error_timestamp": datetime.utcnow().isoformat(),
        "error_message": error_message,
        "action": "certificate-check-error",
    }

    s3.put_object(
        Bucket=bucket_name,
        Key=f"transactions/{transaction_id}/errormetadata.json",
        Body=json.dumps(error_metadata, indent=2),
        ServerSideEncryption="aws:kms",
    )
    logger.info("Error metadata stored in S3: transactions/%s/errormetadata.json", transaction_id)


def handle_existing_certificate(certificate_data, domain, transaction_id):
    """Handle logic when certificate exists in ACM."""
    cert_arn = certificate_data["certificate_arn"]
    logger.info("Found certificate: %s", cert_arn)

    # Check certificate expiration
    check_result = is_certificate_expired(certificate_data["detail"])
    
    # Extract expiration details
    is_expired = check_result["is_expired"]
    is_expiring_soon = check_result["is_expiring_soon"]
    expiration_date = check_result["expiration_date"]

    # Store metadata in S3
    store_check_metadata(transaction_id, domain, certificate_data, check_result)

    if is_expired or is_expiring_soon:
        logger.warning(
            "Certificate is expired or expiring soon. Expired: %s, Expiring soon: %s",
            is_expired,
            is_expiring_soon,
        )
        response = create_response(
            expired=True,
            domain=domain,
            transaction_id=transaction_id,
            certificate_arn=cert_arn,
            expiration_date=expiration_date,
            reason="Certificate expired or expiring soon",
        )
    else:
        logger.info("Certificate is valid and not expiring soon")
        response = create_response(
            expired=False,
            domain=domain,
            transaction_id=transaction_id,
            certificate_arn=cert_arn,
            expiration_date=expiration_date,
        )

    logger.info("Certificate check completed: %s", response)
    return response


def handle_missing_certificate(domain, transaction_id):
    """Handle logic when no certificate is found in ACM."""
    logger.warning("No certificate found in ACM for domain: %s", domain)
    store_check_metadata(transaction_id, domain, None, {})

    response = create_response(
        expired=True,
        domain=domain,
        transaction_id=transaction_id,
        reason="No certificate found in ACM",
    )
    
    logger.info("Certificate check completed - not found: %s", response)
    return response


def create_response(expired, domain, transaction_id, certificate_arn=None, expiration_date=None, reason=None):
    """Create standardized Lambda response."""
    logger.debug("Creating response - expired: %s, domain: %s", expired, domain)

    response = {
        "expired": expired,
        "domain": domain,
        "transaction_id": transaction_id,
        "bucket_name": bucket_name,  # Use the global bucket_name
    }

    # Add optional fields if provided
    if certificate_arn:
        response["certificate_arn"] = certificate_arn
    if expiration_date:
        response["expiration_date"] = expiration_date
    if reason:
        response["reason"] = reason

    return response