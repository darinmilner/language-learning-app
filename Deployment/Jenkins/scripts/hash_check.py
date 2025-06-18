import os
import sys
import argparse
import hashlib
import boto3
from botocore.exceptions import ClientError

def compute_directory_hash(directory):
    """Compute SHA256 hash for a directory's contents"""
    hash_obj = hashlib.sha256()
    
    if not os.path.exists(directory):
        raise ValueError(f"Directory not found: {directory}")
    
    # Walk through all files in directory
    all_files = []
    for root, _, files in os.walk(directory):
        for filename in files:
            file_path = os.path.join(root, filename)
            if os.path.isfile(file_path):
                rel_path = os.path.relpath(file_path, directory)
                all_files.append((rel_path, file_path))
    
    # Sort files by relative path for consistent hashing
    all_files.sort(key=lambda x: x[0])
    
    for rel_path, abs_path in all_files:
        # Include relative path in hash
        hash_obj.update(rel_path.encode('utf-8'))
        
        # Include file content in hash
        with open(abs_path, 'rb') as f:
            while chunk := f.read(8192):
                hash_obj.update(chunk)
    
    return hash_obj.hexdigest()

def main():
    parser = argparse.ArgumentParser(description='Check Lambda code changes against S3 hashes')
    parser.add_argument('--s3-bucket', required=True, help='S3 bucket name')
    parser.add_argument('--key-prefix', default='lambda_hashes', help='S3 key prefix')
    parser.add_argument('--update', action='store_true', help='Update hashes in S3 after verification')
    parser.add_argument('directories', nargs='+', help='Lambda directories to check')
    args = parser.parse_args()

    s3 = boto3.client('s3')
    changed_dirs = []
    hash_map = {}

    # Compute current hashes
    for directory in args.directories:
        try:
            current_hash = compute_directory_hash(directory)
            hash_map[directory] = current_hash
            print(f"Computed hash for {directory}: {current_hash}")
        except Exception as e:
            print(f"Error processing {directory}: {str(e)}", file=sys.stderr)
            sys.exit(1)

    # Check against S3 hashes
    for directory, current_hash in hash_map.items():
        s3_key = f"{args.key_prefix}/{os.path.basename(directory)}.hash"
        try:
            response = s3.get_object(Bucket=args.s3_bucket, Key=s3_key)
            stored_hash = response['Body'].read().decode('utf-8').strip()
            
            if stored_hash != current_hash:
                print(f"Change detected in {directory}")
                changed_dirs.append(directory)
            else:
                print(f"No changes in {directory}")
                
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                print(f"No previous hash found for {directory} - treating as changed")
                changed_dirs.append(directory)
            else:
                raise

    # Update hashes in S3 if requested
    if args.update and changed_dirs:
        for directory in changed_dirs:
            s3_key = f"{args.key_prefix}/{os.path.basename(directory)}.hash"
            s3.put_object(
                Bucket=args.s3_bucket,
                Key=s3_key,
                Body=hash_map[directory],
                ContentType='text/plain'
            )
            print(f"Updated hash in S3 for {directory}")

    # Exit codes: 0 = no changes, 1 = changes detected
    sys.exit(1 if changed_dirs else 0)

if __name__ == "__main__":
    main()