## Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.
## SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
## Licensed under the Amazon Software License  https://aws.amazon.com/asl/
import json
from helper import * 
import os
from urllib.parse import unquote_plus

def lambda_handler(event, context):
    print(event)
    try:
        key = event["Records"][0]["s3"]["object"]["key"]
        invoices_bda_queue_url = os.getenv("INVOICES_BDA_QUEUE_URL", "")
        
    except:
        print("in dev mode")
        key = ""
        invoices_bda_queue_url = ""

    doc_type_folder_name = unquote_plus(key.split("/")[0])

    if doc_type_folder_name == "invoices":
        response = send_message_to_sqs(invoices_bda_queue_url, event)
    else:
        response = "Invalid Document Type!! Please upload the files to the designated folder: invoices"
        print(response)

    return {'statusCode': 200,
            'body': json.dumps({'course_content': response})
    }


if __name__ == "__main__":
    event = None
    lambda_handler(event, None)