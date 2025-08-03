# Add retry to upload command
max_retries=5
retry_delay=2

for i in $(seq 1 $max_retries); do
  echo "Upload attempt $i/$max_retries"
  aws s3 cp file.zip s3://bucket/path/ && break || sleep $(($retry_delay * $i))
done