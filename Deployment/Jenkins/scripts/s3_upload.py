import boto3
from botocore.config import Config

s3 = boto3.client('s3', config=Config(
    connect_timeout=30,
    read_timeout=60,
    retries={'max_attempts': 3}
))

s3.upload_file('largefile.zip', 'my-bucket', 'path/largefile.zip')
