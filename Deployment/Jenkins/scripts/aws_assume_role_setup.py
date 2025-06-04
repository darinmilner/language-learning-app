# aws_assume_role_setup.py

import boto3
import os
import subprocess
import sys
import platform


def install_aws_cli():
    """Downloads and installs the AWS CLI v2 (Linux only in this example)."""
    if platform.system().lower() != "linux":
        raise Exception("This installer currently supports Linux only.")

    subprocess.run([
        "curl", "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip",
        "-o", "awscliv2.zip"
    ], check=True)
    subprocess.run(["unzip", "-o", "awscliv2.zip"], check=True)
    subprocess.run(["sudo", "./aws/install", "--update"], check=True)


def assume_iam_role(role_arn, session_name="jenkins-tf"):
    """Assumes an IAM role and returns temporary credentials."""
    sts = boto3.client("sts")
    response = sts.assume_role(
        RoleArn=role_arn,
        RoleSessionName=session_name
    )
    return response["Credentials"]


def configure_aws_cli(creds, region):
    """Writes temporary credentials to AWS CLI config."""
    aws_dir = os.path.expanduser("~/.aws")
    os.makedirs(aws_dir, exist_ok=True)

    with open(os.path.join(aws_dir, "credentials"), "w") as cred_file:
        cred_file.write(f"""[default]
aws_access_key_id = {creds['AccessKeyId']}
aws_secret_access_key = {creds['SecretAccessKey']}
aws_session_token = {creds['SessionToken']}
""")

    with open(os.path.join(aws_dir, "config"), "w") as config_file:
        config_file.write(f"""[default]
region = {region}
output = json
""")


if __name__ == "__main__":
    role_arn = os.getenv("ASSUME_ROLE_ARN")
    region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

    if not role_arn:
        print("ASSUME_ROLE_ARN is required.")
        sys.exit(1)

    try:
        install_aws_cli()
        creds = assume_iam_role(role_arn)
        configure_aws_cli(creds, region)
        print("AWS CLI configured with assumed role.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
