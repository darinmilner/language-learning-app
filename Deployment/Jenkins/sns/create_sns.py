"""
Creates an SNS Topic
"""

import boto3
import botocore


def create_sns_topic(name, display_name, key, value):
    """
    Creates an SNS topic and prints the ARN

    Args:
        name (str) Name of the SNS Topic
        display_name (str) The Display Name of the SNS Topic
        key (str) Tag key
        value (str) Tag value
    """

    try:
        sns_resource = boto3.resource("sns")
        topic = sns_resource.create_topic(
            Name=name,
            Attributes={"DisplayName": display_name},
            Tags=[{"Key": key, "Value": value}],
        )

        print(f"SNS Topic has been created {topic.arn}")
    except botocore.exceptions.ClientError as e:
        print(e.response["Error"]["Message"])
    except botocore.exceptions.ParamValidationError as e:
        print(e)


try:
    topic_name = input("Enter the topic name:  ")
    topic_display_name = input("Enter the topic display name:  ")
    tag_key = input("Enter the tag key:  ")
    tag_value = input("Enter the tag value:  ")

    create_sns_topic(topic_name, topic_display_name, tag_key, tag_value)
except ValueError as val_error:
    print(val_error)
except KeyboardInterrupt:
    print("Keyboard Interrupt! Shutting Down!")