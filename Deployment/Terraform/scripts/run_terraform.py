import subprocess
# import boto3
import os


def run_terraform(command, args=None, role_arn=None, session_name="jenkins-tf"):
    """
    Runs a Terraform command with AWS credentials from an assumed role.

    Parameters:
    - command (str): Terraform command to run (e.g., 'init', 'apply', 'destroy').
    - args (list[str], optional): Additional arguments for the command.
    - role_arn (str, optional): IAM Role ARN to assume. Defaults to a hardcoded example.
    - session_name (str): The session name for the STS role assumption.

    Returns:
    - dict: {
        "success": bool,
        "stdout": str,
        "stderr": str,
        "returncode": int
      }
    """
    if args is None:
        args = []

    # Use a default role if not provided
    role_arn = role_arn or 'arn:aws:iam::123456789012:role/JenkinsTerraformRole'

    try:
        # Assume role via STS
        # sts = boto3.client('sts')
        # creds = sts.assume_role(
        #     RoleArn=role_arn,
        #     RoleSessionName=session_name
        # )['Credentials']

        # # Build environment with temporary credentials
        # env = {
        #     **os.environ,
        #     "AWS_ACCESS_KEY_ID": creds['AccessKeyId'],
        #     "AWS_SECRET_ACCESS_KEY": creds['SecretAccessKey'],
        #     "AWS_SESSION_TOKEN": creds['SessionToken']
        # }

        # Build the Terraform command
        terraform_cmd = ['terraform', command] + args

        result = subprocess.run(
            terraform_cmd,
            # env=env,
            capture_output=True,
            check=False  # We handle errors manually
        )

        return {
            "success": result.returncode == 0,
            "stdout": result.stdout.decode(),
            "stderr": result.stderr.decode(),
            "returncode": result.returncode
        }

    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "returncode": -1
        }
        
response = run_terraform("destroy", args=["-auto-approve"])

if response['success']:
    print("Terraform apply succeeded:\n", response['stdout'])
else:
    print("Terraform apply failed:\n", response['stderr'])
