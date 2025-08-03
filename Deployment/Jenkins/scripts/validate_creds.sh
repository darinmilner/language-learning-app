# Check credential validity
aws sts get-caller-identity

# Verify S3 bucket access
aws s3 ls s3://${BUCKET_NAME} --region ${AWS_REGION}

# Test minimal S3 permissions
aws s3api head-bucket --bucket ${BUCKET_NAME}

# Check session token expiration (if using temporary credentials)
aws sts get-session-token