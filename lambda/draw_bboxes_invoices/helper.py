## Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.
## SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
## Licensed under the Amazon Software License  https://aws.amazon.com/asl/
import boto3
from botocore.config import Config
from io import BytesIO
from urllib.parse import urlparse, unquote_plus
import json
import os
import time
from PIL import Image, ImageDraw, ImageFont
import pypdfium2


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

def save_image_to_s3(image, bucket, key):
    with BytesIO() as image_buffer:
        image.save(image_buffer, 'PNG')
        image_buffer.seek(0)
        s3_client.upload_fileobj(image_buffer, bucket, key)
    return bucket, key

def convert_pdf_to_png(input_bucket, input_key, output_bucket, output_key):
    pdf_obj = s3_resource.Object(input_bucket, input_key).get()['Body'].read()
    pdf = pypdfium2.PdfDocument(pdf_obj)
    n_pages = len(pdf)  # get the number of pages in the document
    print("Number of pages:", n_pages)
    page = pdf[0] # we will take first page only
    bitmap = page.render(scale=2, rotation=0)
    pil_image = bitmap.to_pil()
    save_image_to_s3(pil_image, output_bucket, output_key)
    return output_bucket, output_key

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


def invoke_data_automation(input_s3_uri, output_s3_uri, blueprint_arn):
    response = bda_runtime_client.invoke_data_automation_async(
                                inputConfiguration={
                                    's3Uri': input_s3_uri
                                },
                                outputConfiguration={
                                    's3Uri': output_s3_uri
                                },
                                notificationConfiguration={
                                    'eventBridgeConfiguration': {
                                        'eventBridgeEnabled': True
                                    }
                                },
                                blueprints=[{'blueprintArn': blueprint_arn},]
                            )
    return response

def check_data_automation_job_status(invocation_arn):
    while True:
        job_status_response = bda_runtime_client.get_data_automation_status(
            invocationArn=invocation_arn
        )
        
        status = job_status_response['status']  # Assuming the status is in this field
        job_metadata_s3_uri = ""
        
        if status == 'InProgress':
            print("Job is still in progress. Waiting...")
            time.sleep(5)  # Wait for 5 seconds before checking again
            continue
        elif status == 'Success':
            print("Job completed successfully!")
            job_metadata_s3_uri = job_status_response['outputConfiguration']['s3Uri']
            return 'Success', job_metadata_s3_uri
        elif status in ['ServiceError', 'ClientError', 'Created']:
            print(f"Job ended with status: {status}")
            job_metadata_s3_uri = job_status_response['outputConfiguration']['s3Uri']
            return status, job_metadata_s3_uri
        else:
            print(f"Unknown status: {status}")
            return status, job_metadata_s3_uri

def read_json_content_from_s3(s3_path):
    # Parse bucket and key from s3 path
    bucket_name = s3_path.split('/')[2]
    key = '/'.join(s3_path.split('/')[3:])
    
    response = s3_client.get_object(Bucket=bucket_name, Key=key)
    json_content = json.loads(response['Body'].read().decode('utf-8'))
    return json_content
    
def get_custom_output_path(s3_path):
    json_content = read_json_content_from_s3(s3_path)
    custom_output_path = json_content['output_metadata'][0]['segment_metadata'][0]['custom_output_path']
    return custom_output_path


# Function to draw bounding boxes and confidence scores
def draw_invoices_annotations(json_data, draw, image_width, image_height):
    font = ImageFont.load_default()
    for key, value in json_data.items():
        if isinstance(value, dict) and value.get("success"):
            confidence = value.get("confidence", 0)
            for geometry in value.get("geometry", []):
                bbox = geometry['boundingBox']
                left = bbox['left'] * image_width
                top = bbox['top'] * image_height
                width = bbox['width'] * image_width
                height = bbox['height'] * image_height
                right = left + width
                bottom = top + height

                # Draw the bounding box
                draw.rectangle([left, top, right, bottom], outline="red", width=2)

                # Annotate with confidence score
                text = f"{key}: {confidence:.2f}"
                text_position = (left, top - 10)
                draw.text(text_position, text, fill="red", font=font)
                
        elif isinstance(value, list):  # For nested drug details or similar
            for item in value:
                draw_invoices_annotations(item, draw, image_width, image_height)
                         
def annotate_form_and_save_to_s3(input_s3_uri, json_data, op_bucket, op_key, doc_type):
    # Parse S3 URI
    bucket_name = input_s3_uri.split('/')[2]
    key = '/'.join(input_s3_uri.split('/')[3:])
    
    # Download the image from S3
    response = s3_client.get_object(Bucket=bucket_name, Key=key)
    image_data = response['Body'].read()
    
    # Load image into PIL
    image = Image.open(BytesIO(image_data))
    draw = ImageDraw.Draw(image)
    
    # Get image dimensions
    image_width, image_height = image.size
    
    # Annotate the image
    if doc_type =="invoices":
        draw_invoices_annotations(json_data, draw, image_width, image_height)
    
    # Display the image in the notebook
    # plt.figure(figsize=(15, 15))
    # plt.imshow(image)
    # plt.axis('off')  # Hide axes
    # plt.show()
    
    # Save the image to a BytesIO object
    img_byte_arr = BytesIO()
    image.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()
    
    # Upload the image to S3
    s3_client.put_object(Body=img_byte_arr, Bucket=op_bucket, Key=op_key)
    
    print(f"Annotated image saved to S3: s3://{op_bucket}/{op_key}")

def get_s3_bucket_and_key(s3_input_uri):
    parsed_uri = urlparse(s3_input_uri)
    
    if parsed_uri.scheme == 's3':
        # s3://bucket-name/key format
        bucket = parsed_uri.netloc
        key = parsed_uri.path.lstrip('/')
    elif parsed_uri.scheme == 'https':
        # https://bucket-name.s3.amazonaws.com/key format
        bucket = parsed_uri.netloc.split('.')[0]
        key = parsed_uri.path.lstrip('/')
    else:
        raise ValueError("Unsupported URL format")
    
    # remove un necesssary special quotes
    key = unquote_plus(key)

    return bucket, key
    
def save_json_to_s3(bucket, key, llm_json_response):
    # Convert the dictionary to a JSON string
    json_content = json.dumps(llm_json_response, indent=4)
    # Save the JSON string to S3 (S3 expects bytes, so we encode the string to bytes)
    s3_client.put_object(Bucket=bucket, Key=key, Body=json_content.encode('utf-8'))

def list_s3_items(bucket_name, prefix):
    items = []
    paginator = s3_client.get_paginator('list_objects_v2')
    
    # The S3 API returns results in pages, so we use a paginator
    for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
        if 'Contents' in page:
            for obj in page['Contents']:
                key = obj['Key']
                # Only include the key if it's not the prefix itself and it's not empty
                if key != prefix and key.strip():
                    full_uri = f"s3://{bucket_name}/{key}"
                    items.append(full_uri)
    
    return items

def get_parameter_from_ssm(param_name):
    response = ssm.get_parameter(
            Name=param_name,
            WithDecryption=True
        )
    param_value = response['Parameter']['Value']
    return param_value