# aws_setup.py

import os
import subprocess
import sys
import platform


def install_aws_cli():
    """Downloads and installs the AWS CLI v2 (Linux only in this example)."""
    system = platform.system().lower()

    if system != "linux":
        raise Exception("This installer currently supports Linux only.")

    print("Downloading AWS CLI v2 installer...")

    subprocess.run([
        "curl", "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip",
        "-o", "awscliv2.zip"
    ], check=True)

    subprocess.run(["unzip", "-o", "awscliv2.zip"], check=True)
    subprocess.run(["sudo", "./aws/install", "--update"], check=True)

    print("AWS CLI installed successfully.")


def configure_aws_cli(aws_access_key, aws_secret_key, aws_region):
    """Configures AWS CLI credentials and default region."""
    aws_dir = os.path.expanduser("~/.aws")
    os.makedirs(aws_dir, exist_ok=True)

    credentials_content = f"""
[default]
aws_access_key_id = {aws_access_key}
aws_secret_access_key = {aws_secret_key}
"""

    config_content = f"""
[default]
region = {aws_region}
output = json
"""

    with open(os.path.join(aws_dir, "credentials"), "w") as cred_file:
        cred_file.write(credentials_content.strip())

    with open(os.path.join(aws_dir, "config"), "w") as config_file:
        config_file.write(config_content.strip())

    print("AWS CLI configured successfully.")


if __name__ == "__main__":
    # Get credentials and region from environment (or Jenkins credentials)
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

    if not all([access_key, secret_key]):
        print("Missing AWS credentials in environment variables.")
        sys.exit(1)

    try:
        install_aws_cli()
        configure_aws_cli(access_key, secret_key, region)
    except Exception as e:
        print(f"Setup failed: {e}")
        sys.exit(1)
