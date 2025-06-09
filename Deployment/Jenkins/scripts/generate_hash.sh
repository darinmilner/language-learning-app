#!/bin/bash
LAMBDA_DIR="path/to/lambda/src"  # Change to your Lambda code directory
HASH_FILE="lambda_hash.txt"

# Generate a hash of all files in the directory
find "$LAMBDA_DIR" -type f -exec sha256sum {} + | sort -k 2 | sha256sum | cut -d' ' -f1 > "$HASH_FILE"