# Configure multipart thresholds
aws configure set default.s3.multipart_threshold 64MB
aws configure set default.s3.multipart_chunksize 16MB

# Use sync instead of cp for large directories
aws s3 sync ./dist s3://${BUCKET_NAME}/path/ \
  --delete