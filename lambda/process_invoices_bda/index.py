## Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.
## SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
## Licensed under the Amazon Software License  https://aws.amazon.com/asl/
import json
from helper import * 
import os
from urllib.parse import urlparse, unquote_plus

def lambda_handler(event, context):
    print(event)
    event = json.loads(event['Records'][0]['body'])
    print("event****", event)
    try:
        input_bucket = event["Records"][0]["s3"]["bucket"]["name"]
        key = event["Records"][0]["s3"]["object"]["key"]
        key = unquote_plus(key)
        ## os variables
        stagging_bucket = os.getenv("STAGGING_BUCKET", "")
        output_bucket = os.getenv("OUTPUT_BUCKET", "")
        ssm_param_name = os.getenv("SSM_PARAMETER_NAME", "/my-demo/inovices_blueprint_arn")

    except:
        print("dev mode activated")
        input_bucket=""
        stagging_bucket = ""
        key="invoices/test_invoice_0_1.pdf"
        output_bucket = ""
        ssm_param_name = "/my-demo/inovices_blueprint_arn"

    ## consutructing paths
    input_s3_uri = f"s3://{input_bucket}/{key}"
    job_output_s3_uri = f"s3://{output_bucket}/raw_bda_job_outputs"
    
    ## Lets check if the file is pdf of png
    file_extension = key.split(".")[-1]
    if file_extension == "pdf":
        print("PDF file detected")
        _, key = convert_pdf_to_png(input_bucket, key, stagging_bucket, f"{key}.png")
        input_s3_uri = f"s3://{stagging_bucket}/{key}"
    
    blueprint_arn = get_parameter_from_ssm(ssm_param_name)

    ## Invoke the data automation job
    invoke_response = invoke_data_automation(input_s3_uri, job_output_s3_uri, blueprint_arn)
    invocation_arn = invoke_response['invocationArn']
    print("Job successfully invoked with invocation_arn", invocation_arn)
        
    return {'statusCode': 200,
            'body': json.dumps({
                        'invoke_response': invoke_response
                    })
        }


if __name__ == "__main__":
    event = None
    lambda_handler(event, None)