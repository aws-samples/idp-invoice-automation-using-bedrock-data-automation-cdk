## Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.
## SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
## Licensed under the Amazon Software License  https://aws.amazon.com/asl/
from helper import * 
import os
from urllib.parse import urlparse, unquote_plus

def lambda_handler(event, context):
    print(event)
    
    if event['RequestType'] != 'Create':
        return
    
    # Get Collection name
    inovices_blueprint_name = event.get('ResourceProperties', dict()).get('inovices_blueprint_name')
    blueprint_file_name = "invoices_blueprint.json"

    inovices_blueprint_arn = get_or_create_blueprint(inovices_blueprint_name, blueprint_file_name)
    ssm_param_name = os.getenv("SSM_PARAMETER_NAME", "/my-demo/inovices_blueprint_arn")
    ssm_param_value = inovices_blueprint_arn
    response = put_parameter_in_ssm(ssm_param_name, ssm_param_value)
    print(response)

    
    return {'statusCode': 200,
             'body': json.dumps({'course_content': response})
    }


if __name__ == "__main__":
    event = None
    lambda_handler(event, None)