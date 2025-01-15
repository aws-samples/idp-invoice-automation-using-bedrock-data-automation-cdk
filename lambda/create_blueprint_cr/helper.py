## Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.
## SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
## Licensed under the Amazon Software License  https://aws.amazon.com/asl/
import boto3
from botocore.config import Config
import json


#increase the standard time out limits in boto3, because Bedrock may take a while to respond to large requests.
my_config = Config(
    connect_timeout=60*5,
    read_timeout=60*5,
)

s3_client=boto3.client("s3")
s3_resource = boto3.resource('s3')
ssm = boto3.client('ssm')
bda_client = boto3.client('bedrock-data-automation')
bda_runtime_client = boto3.client('bedrock-data-automation-runtime')

# read json file from 'blueprints' folder. Json file name is bda_invoices_blueprint.json. this json schmea i need to pass as string to another method. 
def read_json_as_str(file_name):
    # json_file_path = os.path.join(folder_name, file_name)
    
    # Read the JSON file
    with open(file_name, 'r') as file:
        blueprint_schema = json.load(file)
        # Convert the JSON to a string
        schema_string = json.dumps(blueprint_schema)
    return schema_string

def create_blueprint(blueprint_name, schema_str):
    response = bda_client.create_blueprint(
        blueprintName=blueprint_name,
        type='DOCUMENT',
        blueprintStage='LIVE',
        schema=schema_str
    )
    return response

def create_blueprint_version(blueprint_arn):
    response = bda_client.create_blueprint_version(
        blueprintArn=blueprint_arn
    )
    return response

def get_or_create_blueprint(blueprint_name, blueprint_file_name):
        blueprint_arn = ""
        all_blueprint_response = bda_client.list_blueprints(blueprintStageFilter='LIVE')
        for item in all_blueprint_response['blueprints']:
            if blueprint_name in item['blueprintName']:
                blueprint_arn = item['blueprintArn']
                break 
        if blueprint_arn == "":
            print("Blueprint not found")
            blueprint_schema = read_json_as_str(blueprint_file_name)
            blueprint_response = create_blueprint(blueprint_name, blueprint_schema)
            blueprint_arn = blueprint_response['blueprint']['blueprintArn']
        return blueprint_arn

def put_parameter_in_ssm(param_name, param_value):
    response = ssm.put_parameter(
            Name=param_name,
            Value=param_value,
            Type='String',
            Overwrite=True
        )
    return response

