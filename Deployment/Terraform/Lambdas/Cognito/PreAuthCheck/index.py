import os
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    # Get forbidden words from environment variable
    forbidden_words = [word.strip().lower() for word in os.environ.get('FORBIDDEN_WORDS', '').split(',') if word.strip()]
    
    # Extract IAM role ARN from custom attribute
    user_attributes = event['request']['userAttributes']
    role_arn = user_attributes.get('custom:iam_role_arn')
    
    if not role_arn:
        logger.info("No IAM role ARN found in user attributes")
        return event
    
    # Extract role name from ARN
    try:
        role_name = role_arn.split('/')[-1]
    except IndexError:
        logger.error(f"Invalid role ARN format: {role_arn}")
        return event
    
    # Check for forbidden words in role tags
    try:
        if contains_forbidden_tags(role_name, forbidden_words):
            raise Exception("Forbidden word found in role tags")
    except Exception as e:
        logger.error(f"Tag validation failed: {str(e)}")
        raise
    
    return event

def contains_forbidden_tags(role_name, forbidden_words):
    if not forbidden_words:
        logger.info("No forbidden words configured")
        return False
    
    iam = boto3.client('iam')
    paginator = iam.get_paginator('list_role_tags')
    found_forbidden = False
    
    for page in paginator.paginate(RoleName=role_name):
        for tag in page.get('Tags', []):
            tag_value = tag.get('Value', '').lower()
            
            for word in forbidden_words:
                if word and word in tag_value:
                    logger.warning(f"Found forbidden word '{word}' in tag: {tag.get('Key')}='{tag_value}'")
                    found_forbidden = True
    
    return found_forbidden