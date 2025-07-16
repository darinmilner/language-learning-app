Overview
This project provides a secure, automated solution for managing SSL/TLS certificates for domains hosted on AWS Route53. The Jenkins pipeline checks for existing valid certificates in AWS Certificate Manager (ACM), generates new certificates using Certbot when needed, and securely imports them into ACM using AWS Lambda for enhanced security.

Key Features
Secure Certificate Generation: Uses Certbot in isolated Docker containers

Zero Persistent Secrets: Ephemeral credentials and automatic cleanup

GPG Encryption: Private keys encrypted before transfer

AWS API Integration: Direct SDK calls instead of CLI

Modular Design: Reusable Groovy functions for AWS operations

Lambda Integration: Secure certificate import using serverless functions

Pipeline Parameters
Parameter	Default	Description
DOMAIN	example.com	Domain for SSL certificate
EMAIL	admin@example.com	Notification email
AWS_REGION	us-east-1	AWS region for ACM operations

Security Features
Ephemeral Environments:

Temporary S3 buckets per pipeline run

GPG keys rotated after each execution

Docker containers destroyed after use

Encryption:

Private key encrypted with GPG before upload

S3 server-side encryption (AES256)

Secrets stored in Jenkins credentials store

Access Control:

Least privilege IAM policies

AWS API calls instead of CLI

Lambda execution in isolated environment

Audit Trails:

CloudTrail logs for AWS operations

Jenkins build history with parameters

S3 access logs for file transfers

Troubleshooting
Common Issues
Certificate Validation Failures:

Ensure Route53 hosted zone exists

Verify IAM permissions for Route53

Check DNS propagation status

Lambda Timeouts:

Increase timeout to 1 minute

Set memory to 512MB

Check CloudWatch logs for errors