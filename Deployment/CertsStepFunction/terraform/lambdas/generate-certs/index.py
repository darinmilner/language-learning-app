import json
import logging
import os
import tempfile
import subprocess
from datetime import datetime

import boto3
from cryptography import x509
from cryptography.hazmat.backends import default_backend

# Initialize AWS clients and environment variables
s3 = boto3.client("s3")
bucket_name = os.environ.get("S3_BUCKET")
certbot_email = os.environ.get("CERTBOT_EMAIL", "admin@example.com")
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()

# Configure logging
logger = logging.getLogger()
logger.setLevel(getattr(logging, log_level, logging.INFO))


def lambda_handler(event, context):
    """Lambda handler to generate certificates using Certbot."""
    domain = event["domain"]
    transaction_id = event["transaction_id"]
    old_cert_arn = event.get("certificate_arn")

    logger.info("Starting certificate generation for domain: %s", domain)
    logger.debug("Event: %s", event)

    if not bucket_name:
        logger.error("S3_BUCKET environment variable is required but not set")
        raise ValueError("S3_BUCKET environment variable is required")

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            run_certbot_command(domain, temp_dir)
            certificate, private_key, chain = read_certificate_files(domain, temp_dir)
            expiration_date = get_certificate_expiration(certificate)
            
            upload_certificate_to_s3(domain, certificate, private_key, chain, transaction_id, expiration_date)
            store_generation_metadata(transaction_id, domain, old_cert_arn, expiration_date)

            response = {
                "success": True,
                "domain": domain,
                "transaction_id": transaction_id,
                "bucket_name": bucket_name,
                "expiration_date": expiration_date,
                "s3_location": f"s3://{bucket_name}/certificates/{domain}/"
            }

            logger.info("Certificate generation completed successfully: %s", response)
            return response

        except subprocess.CalledProcessError as e:
            logger.error("Certbot command failed: %s", e.stderr)
            store_generation_error(transaction_id, domain, old_cert_arn, e.stderr)
            return create_error_response(domain, transaction_id, e.stderr)

        except Exception as e:
            logger.error("Unexpected error during certificate generation: %s", str(e), exc_info=True)
            store_generation_error(transaction_id, domain, old_cert_arn, str(e))
            raise e


def run_certbot_command(domain, temp_dir):
    """Run certbot command to generate certificate."""
    logger.info("Executing Certbot command for domain: %s", domain)
    
    result = subprocess.run([
        "certbot", "certonly",
        "--dns-route53",
        "--domains", domain,
        "--non-interactive",
        "--agree-tos",
        "--config-dir", temp_dir,
        "--work-dir", "/tmp",
        "--logs-dir", "/tmp",
        "--email", certbot_email
    ], check=True, capture_output=True, text=True)

    logger.debug("Certbot command executed successfully")
    return result


def read_certificate_files(domain, temp_dir):
    """Read certificate files from filesystem."""
    logger.debug("Reading certificate files from: %s/live/%s/", temp_dir, domain)
    
    cert_path = f"{temp_dir}/live/{domain}/cert.pem"
    key_path = f"{temp_dir}/live/{domain}/privkey.pem"
    chain_path = f"{temp_dir}/live/{domain}/chain.pem"

    with open(cert_path, "r") as f:
        certificate = f.read()

    with open(key_path, "r") as f:
        private_key = f.read()

    with open(chain_path, "r") as f:
        chain = f.read()

    logger.debug("Certificate files read successfully")
    return certificate, private_key, chain


def get_certificate_expiration(certificate_content):
    """Extract expiration date from certificate."""
    logger.debug("Parsing certificate to extract expiration date")
    
    cert_obj = x509.load_pem_x509_certificate(
        certificate_content.encode(),
        default_backend()
    )
    expiration = cert_obj.not_valid_after.isoformat()
    
    logger.debug("Certificate expiration date: %s", expiration)
    return expiration


def upload_certificate_to_s3(domain, certificate, private_key, chain, transaction_id, expiration_date):
    """Upload certificate files to S3 with metadata."""
    logger.info("Uploading certificate files to S3 bucket: %s", bucket_name)

    metadata = {
        "domain": domain,
        "expiration-date": expiration_date,
        "transaction-id": transaction_id,
        "generated-at": datetime.utcnow().isoformat()
    }

    # Upload certificate files
    certificate_files = [
        ("cert.pem", certificate),
        ("privkey.pem", private_key),
        ("chain.pem", chain)
    ]

    for filename, content in certificate_files:
        s3.put_object(
            Bucket=bucket_name,
            Key=f"certificates/{domain}/{filename}",
            Body=content,
            ServerSideEncryption="aws:kms",
            Metadata=metadata
        )
        logger.debug("Uploaded %s to: certificates/%s/%s", filename, domain, filename)

    logger.info("All certificate files uploaded to S3 successfully")


def store_generation_metadata(transaction_id, domain, old_cert_arn, expiration_date):
    """Store certificate generation metadata in S3."""
    logger.debug("Storing generation metadata for transaction: %s", transaction_id)

    metadata = {
        "transaction_id": transaction_id,
        "domain": domain,
        "generation_timestamp": datetime.utcnow().isoformat(),
        "old_certificate_arn": old_cert_arn,
        "action": "certificate_generation",
        "success": True,
        "expiration_date": expiration_date
    }

    s3.put_object(
        Bucket=bucket_name,
        Key=f"transactions/{transaction_id}/generationmetadata.json",
        Body=json.dumps(metadata, indent=2, default=str),
        ServerSideEncryption="aws:kms"
    )
    logger.info("Generation metadata stored in S3: transactions/%s/generationmetadata.json", transaction_id)


def store_generation_error(transaction_id, domain, old_cert_arn, error_message):
    """Store certificate generation error metadata in S3."""
    logger.error("Storing generation error metadata for transaction: %s", transaction_id)

    metadata = {
        "transaction_id": transaction_id,
        "domain": domain,
        "generation_timestamp": datetime.utcnow().isoformat(),
        "old_certificate_arn": old_cert_arn,
        "action": "certificate-generation",
        "success": False,
        "error": error_message
    }

    s3.put_object(
        Bucket=bucket_name,
        Key=f"transactions/{transaction_id}/generationerror.json",
        Body=json.dumps(metadata, indent=2),
        ServerSideEncryption="aws:kms"
    )
    logger.info("Generation error metadata stored in S3: transactions/%s/generationerror.json", transaction_id)


def create_error_response(domain, transaction_id, error_message):
    """Create error response for certificate generation failure."""
    return {
        "success": False,
        "error": f"Certificate generation failed: {error_message}",
        "domain": domain,
        "transaction_id": transaction_id
    }