## Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.
## SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
## Licensed under the Amazon Software License  https://aws.amazon.com/asl/
import json
from helper import * 
import os
from urllib.parse import urlparse, unquote_plus

def lambda_handler(event, context):
    print(event)
    try:
        input_bucket = event["detail"]["input_s3_object"]["s3_bucket"]
        input_key = event["detail"]["input_s3_object"]["name"]
        input_key = unquote_plus(input_key)
        output_bucket = event["detail"]["output_s3_location"]["s3_bucket"]
        output_key = event["detail"]["output_s3_location"]["name"]
        output_key = unquote_plus(output_key)
        doc_type = os.getenv("DOC_TYPE", "invoices")
    except:
        print("dev mode activated")
        input_bucket= ""
        input_key = "invoices/test_invoice_0_1.pdf.png"
        output_bucket = ""
        output_key = "raw_bda_job_outputs/ef33d28a-8503-4cfa-9ea7-1b36ac8de7c2/0"
        doc_type = "invoices"

    output_json_key = f"{input_key}.json"
    output_inference_results_json_key = f"bda_json/inference_results/{output_json_key}"
    output_explainability_info_result_json_key = f"bda_json/explainability_info_result/{output_json_key}"
    output_bbox_image_key = f"bda_bbox_img/{output_json_key.removesuffix('.json')}.png"

    input_s3_uri = f"s3://{input_bucket}/{input_key}"
    
    s3_uri = f"s3://{output_bucket}/{output_key}"
    job_metadata_s3_uri = s3_uri.split("/")[:-1]
    job_metadata_s3_uri = "/".join(job_metadata_s3_uri)
    job_metadata_s3_uri = job_metadata_s3_uri + "/job_metadata.json"
    #Get the Custom blueprint output
    custom_output_s3_uri = get_custom_output_path(job_metadata_s3_uri)

    # Read the json results from output S3 json files
    custom_op_json = read_json_content_from_s3(custom_output_s3_uri)
    inference_results = custom_op_json["inference_result"]
    explainability_info_result = custom_op_json['explainability_info'][0]
    
    # Save the inference results in s3 output bucket
    save_json_to_s3(output_bucket, output_inference_results_json_key, inference_results)
    
    # Save the bounding boxes and all in outuut bucket
    save_json_to_s3(output_bucket, output_explainability_info_result_json_key, explainability_info_result)
    
    # Annotate and save image in output S3 bucket
    annotate_form_and_save_to_s3(input_s3_uri, explainability_info_result, output_bucket, output_bbox_image_key, doc_type=doc_type)
        
    return {'statusCode': 200,
            'body': json.dumps({
                        'event': event
                    })
        }


if __name__ == "__main__":
    event = None
    lambda_handler(event, None)

