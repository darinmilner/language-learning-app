import boto3
import botocore


def create_subscription(topic_name, protocol, endpoint):
    """
    Creates an SNS subscription and prints the ARN

    Args:
        topic_name (str) Name of the SNS Topic
        protocol (str) Subscription protocol
        endpoint (str) Notification endpoint
    """
    try:
        sns_resource = boto3.resource("sns")

        # gets all the topics
        topic_itr = sns_resource.topics.all()
        sns_topic = ""

        for topic in topic_itr:
            if topic.arn.split(":")[-1].lower() == topic_name.lower():
                # assigns the topic resource to the sns_topic variable if the topic
                # matches the desired topic_name
                sns_topic = sns_resource.Topic(topic.arn)

            if sns_topic:
                subscription = sns_topic.subscribe(
                    Protocol=protocol,
                    Endpoint=endpoint,
                    ReturnSubscriptionArn=True,
                )

                print(f"SNS Subscription has been created {subscription.arn}")
            else:
                print(f"SNS Topic {topic_name} has not been found.")

    except botocore.exceptions.ClientError as e:
        print(e.response["Error"]["Message"])
    except botocore.exceptions.ParamValidationError as e:
        print(e)


try:
    top_name = input("Enter the topic name:  ")
    sub_protocol = input("Enter the topic subscription protocol:  ")
    sub_endpoint = input("Enter the subscription endpoint:  ")

    create_subscription(top_name, sub_protocol, sub_endpoint)
except ValueError as val_error:
    print(val_error)
except KeyboardInterrupt:
    print("Keyboard Interrupt! Shutting Down!")