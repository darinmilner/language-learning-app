import boto3
import base64
import docker
import argparse
import sys

# -----------------------------
# Config (edit)
# -----------------------------
AWS_REGION = "us-east-1"
AWS_ACCOUNT_ID = "123456789012"
ECR_REPO = f"{AWS_ACCOUNT_ID}.dkr.ecr.{AWS_REGION}.amazonaws.com/my-repo"

# -----------------------------
# Functions
# -----------------------------

def ecr_login():
    """Log in to ECR using boto3 credentials"""
    ecr = boto3.client("ecr", region_name=AWS_REGION)
    auth = ecr.get_authorization_token()["authorizationData"][0]
    token = base64.b64decode(auth["authorizationToken"]).decode()
    username, password = token.split(":")
    registry = auth["proxyEndpoint"]

    client = docker.from_env()
    client.login(username=username, password=password, registry=registry)
    print(f"✅ Logged in to ECR: {registry}")
    return client

def tag_and_push(client, local_image, tag_suffix="demo"):
    """Tag existing image and push to ECR"""
    # Ensure repo and tag
    if ":" in local_image:
        repo, tag = local_image.split(":")
    else:
        repo = local_image
        tag = "latest"

    full_local_name = f"{repo}:{tag}"
    ecr_tag = f"{ECR_REPO}:{repo}-{tag_suffix}"

    try:
        img = client.images.get(full_local_name)
    except docker.errors.ImageNotFound:
        print(f"❌ Local image not found: {full_local_name}")
        sys.exit(1)

    # Tag the image for ECR
    img.tag(ECR_REPO, f"{repo}-{tag_suffix}")
    print(f"Tagged {full_local_name} as {ecr_tag}")

    # Push
    print(f"Pushing {ecr_tag}...")
    for line in client.images.push(ECR_REPO, f"{repo}-{tag_suffix}", stream=True, decode=True):
        if "status" in line:
            print(line["status"])
        elif "errorDetail" in line:
            print("❌ Push error:", line["errorDetail"])
            sys.exit(1)

    print(f"✅ Successfully pushed {ecr_tag}\n")

# -----------------------------
# CLI
# -----------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Tag and push existing Docker images to ECR (demo-friendly)"
    )
    parser.add_argument(
        "images", nargs="+", help="Local image names to push (repo[:tag])"
    )
    parser.add_argument(
        "--tag", default="demo", help="Suffix to append for ECR tag (default: demo)"
    )
    args = parser.parse_args()

    client = ecr_login()

    for img_name in args.images:
        tag_and_push(client, img_name, args.tag)

    print("🎉 All done!")

if __name__ == "__main__":
    main()
