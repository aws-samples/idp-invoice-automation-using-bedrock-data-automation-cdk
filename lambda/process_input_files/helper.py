## Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.
## SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
## Licensed under the Amazon Software License  https://aws.amazon.com/asl/
import json
import boto3

sns_client = boto3.client('sns')
sqs_client = boto3.client("sqs")

def send_message_to_sqs(queue_url, event):
    message_body = json.dumps(event)
    response = sqs_client.send_message(
        QueueUrl=queue_url,
        DelaySeconds=0,
        MessageBody=(message_body)
    )
    print(f"Message body sent to SQS:: {message_body}")
    return response


def send_message_to_sns(topic_arn, event):
    message_body = json.dumps(event)
    response = sns_client.publish(
        TopicArn=topic_arn,
        Message=message_body
    )
    print(f"Message body sent to SNS:: {message_body}")
    return response