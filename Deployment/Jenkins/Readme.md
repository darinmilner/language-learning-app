# Troubleshooting AWS S3 Upload Hangs in CI/CD Pipelines

![AWS S3 Troubleshooting](https://img.shields.io/badge/AWS-S3-ff9900?logo=amazonaws&logoColor=white&style=flat) ![CI/CD Support](https://img.shields.io/badge/CI%2FCD-Jenkins%20%7C%20GitHub%20Actions%20%7C%20CircleCI-brightgreen?style=flat)

## Common Symptoms 🚨
- AWS CLI `s3 cp` command hangs indefinitely
- Uploads time out after several minutes
- Intermittent failures despite correct credentials
- Pipeline stalls at upload stage
- "Broken pipe" or connection reset errors
- Progress percentage freezes during upload

## Common Causes 🔍

### 🔗 Network Connectivity Issues
- Firewall blocking outbound connections to S3
- Proxy misconfiguration
- Unstable network connections
- DNS resolution failures
- VPC routing problems
- MTU size mismatches

### 🔑 AWS Authentication Problems
- Expired temporary credentials
- Incorrect IAM permissions
- Mismatched AWS region configuration
- Missing S3 bucket policy permissions
- STS token expiration

### ⚙️ AWS CLI Configuration
- Outdated AWS CLI version
- Missing or incorrect credentials profile
- Improper region configuration
- Multipart upload thresholds not configured
- Default timeouts too short

### 🪣 S3 Bucket Issues
- Bucket in wrong region
- Bucket policy restrictions
- KMS key permissions missing
- S3 bucket encryption requirements
- Transfer Acceleration conflicts
- Bucket owner full control ACL missing

### 💻 Resource Constraints
- Insufficient memory/CPU on CI agent
- Network bandwidth limitations
- File handle exhaustion
- Disk I/O bottlenecks
- High latency connections

## Step-by-Step Troubleshooting Guide 🔧

### 1️⃣ Verify Basic Connectivity
```bash
# Test DNS resolution
nslookup s3.${AWS_REGION}.amazonaws.com

# Check TCP connectivity to S3 (port 443)
telnet s3.${AWS_REGION}.amazonaws.com 443

# Alternative using netcat
nc -vz s3.${AWS_REGION}.amazonaws.com 443

# Test HTTP access
curl -I https://s3.${AWS_REGION}.amazonaws.com

# Measure latency (install tcptraceroute first)
sudo apt-get install -y tcptraceroute
alias tcpping='tcptraceroute -n -w 1'
tcpping s3.${AWS_REGION}.amazonaws.com 443